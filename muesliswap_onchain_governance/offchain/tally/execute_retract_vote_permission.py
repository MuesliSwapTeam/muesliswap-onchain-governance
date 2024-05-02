import datetime

import fire
import pycardano

from muesliswap_onchain_governance.onchain.tally.tally import BoxedInt
from muesliswap_onchain_governance.onchain.util import reduced_proposal_params
from muesliswap_onchain_governance.utils.network import (
    show_tx,
    blockfrost_client,
    context,
)
from muesliswap_onchain_governance.utils.to_script_context import to_address
from opshin.prelude import Token, Nothing
from pycardano import (
    OgmiosChainContext,
    TransactionBuilder,
    Redeemer,
    AuxiliaryData,
    AlonzoMetadata,
    Metadata,
    TransactionOutput,
    Value,
)

from muesliswap_onchain_governance.offchain.util import (
    token_from_string,
    asset_from_token,
    with_min_lovelace,
    sorted_utxos,
    amount_of_token_in_value,
)
from muesliswap_onchain_governance.onchain.tally import tally, tally_auth_nft
from muesliswap_onchain_governance.onchain.staking import (
    staking_vote_nft,
    staking,
    vote_permission_nft,
)
from muesliswap_onchain_governance.utils import (
    get_signing_info,
    ogmios_url,
    network,
    kupo_url,
)
from muesliswap_onchain_governance.utils.contracts import (
    get_contract,
    module_name,
    get_ref_utxo,
)
import blockfrost


def main(
    wallet: str = "creator",
    vote_permission_nft_cbor_hex: str = None,
):
    # Load script info
    (
        tally_script,
        _,
        tally_address,
    ) = get_contract(module_name(tally), True)
    tally_script_ref_utxo = get_ref_utxo(tally_script, context)
    (
        staking_script,
        _,
        staking_address,
    ) = get_contract(module_name(staking), True)
    staking_script_ref_utxo = get_ref_utxo(staking_script, context)
    (
        staking_vote_nft_script,
        staking_vote_nft_policy_id,
        _,
    ) = get_contract(module_name(staking_vote_nft), True)
    staking_vote_nft_script_ref_utxo = get_ref_utxo(staking_vote_nft_script, context)
    (
        _,
        tally_auth_nft_policy_id,
        _,
    ) = get_contract(module_name(tally_auth_nft), True)
    (
        vote_permission_nft_script,
        vote_permission_nft_policy_id,
        _,
    ) = get_contract(module_name(vote_permission_nft), True)
    vote_permission_nft_script_ref_utxo = get_ref_utxo(
        vote_permission_nft_script, context
    )

    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )

    # find staking position with vote permission
    staking_utxos = context.utxos(staking_address)
    staking_utxo = None
    for u in staking_utxos:
        try:
            prev_staking_datum = staking.StakingState.from_cbor(u.output.datum.cbor)
        except Exception as e:
            continue
        if prev_staking_datum.params.owner == to_address(payment_address):
            continue
        if not u.output.amount.multi_asset.get(
            pycardano.ScriptHash(vote_permission_nft_policy_id.payload), {}
        ):
            continue
        staking_utxo = u
        break
    assert staking_utxo, "Staking position with vote permission not found"

    vote_permission_nft_tk = Token(
        vote_permission_nft_policy_id.payload,
        list(
            staking_utxo.output.amount.multi_asset.get(
                pycardano.ScriptHash(vote_permission_nft_policy_id.payload), {}
            ).keys()
        )[0].payload,
    )
    # We can simply look this up because the token name is the same as the datum hash of the redeemer during minting - it is hence known to most indexers
    if vote_permission_nft_cbor_hex is None:
        vote_permission_raw_cbor = blockfrost_client.script_datum_cbor(
            vote_permission_nft_tk.token_name.hex()
        ).cbor
    else:
        vote_permission_raw_cbor = vote_permission_nft_cbor_hex
    vote_permission = vote_permission_nft.VotePermissionNFTParams.from_cbor(
        vote_permission_raw_cbor
    )
    assert isinstance(
        vote_permission.redeemer, vote_permission_nft.DelegatedRetractVote
    ), "Only retract vote permissions are supported by this script"
    proposal_id = vote_permission.redeemer.participation.tally_params.proposal_id

    tally_auth_nft_tk = (
        vote_permission.redeemer.participation.tally_params.tally_auth_nft
    )
    # Select tally
    tally_utxos = context.utxos(tally_address)
    tally_utxo = None
    for u in tally_utxos:
        if not amount_of_token_in_value(tally_auth_nft_tk, u.output.amount):
            continue
        prev_tally_datum = tally.TallyState.from_cbor(u.output.datum.cbor)
        if prev_tally_datum.params.proposal_id == proposal_id:
            tally_utxo = u
            break
    assert tally_utxo, "Tally with given proposal id not found"

    voting_power = vote_permission.redeemer.participation.weight
    proposal_index = vote_permission.redeemer.participation.proposal_index

    payment_utxos = context.utxos(payment_address)
    all_inputs = sorted_utxos(
        [tally_utxo] + [staking_utxo] + payment_utxos,
    )
    tally_input_index = all_inputs.index(tally_utxo)
    staking_input_index = all_inputs.index(staking_utxo)
    staking_participation_index = prev_staking_datum.participations.index(
        vote_permission.redeemer.participation
    )

    # generate redeemer for the tally
    tally_redeemer = Redeemer(
        tally.RetractTallyVote(
            proposal_index=proposal_index,
            weight=voting_power,
            voter_address=vote_permission.owner,
            tally_input_index=tally_input_index,
            tally_output_index=0,
            staking_output_index=1,
            staking_participation_index=staking_participation_index,
        )
    )

    # Make the new datum of the Tally
    new_tally_votes = prev_tally_datum.votes.copy()
    new_tally_votes[proposal_index] -= voting_power
    new_tally_datum = tally.TallyState(
        params=prev_tally_datum.params,
        votes=new_tally_votes,
    )

    # generate redeemer for the staking
    participation = vote_permission.redeemer.participation
    staking_redeemer = Redeemer(
        staking.RetractVote(
            state_input_index=staking_input_index,
            state_output_index=1,
            participation_index=staking_participation_index,
            tally_input_index=tally_input_index,
        )
    )
    # generate the new datum for the staking
    new_staking_participations = prev_staking_datum.participations.copy()
    new_staking_participations.pop(staking_participation_index)
    new_staking_datum = staking.StakingState(
        params=prev_staking_datum.params,
        participations=new_staking_participations,
    )

    # generate the redeemer for the staking vote nft
    staking_vote_nft_redeemer = Redeemer(staking_vote_nft.BurnRedeemer())
    staking_vote_nft_name = staking_vote_nft.staking_vote_nft_name(
        proposal_index,
        voting_power,
        reduced_proposal_params(prev_tally_datum.params),
    )
    staking_vote_nft_tk = Token(
        staking_vote_nft_policy_id.payload, staking_vote_nft_name
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Retract Vote in Tally (delegated)"]}})
        )
    )
    for u in payment_utxos:
        builder.add_input(u)
    builder.add_script_input(
        tally_utxo, tally_script_ref_utxo or tally_script, None, tally_redeemer
    )
    builder.add_script_input(
        staking_utxo, staking_script_ref_utxo or staking_script, None, staking_redeemer
    )

    builder.add_minting_script(
        staking_vote_nft_script_ref_utxo or staking_vote_nft_script,
        staking_vote_nft_redeemer,
    )
    builder.add_minting_script(
        vote_permission_nft_script_ref_utxo or vote_permission_nft_script,
        Redeemer(Nothing()),
    )
    builder.mint = asset_from_token(staking_vote_nft_tk, -1) + asset_from_token(
        vote_permission_nft_tk, -1
    )
    tally_output = TransactionOutput(
        address=tally_address,
        amount=tally_utxo.output.amount,
        datum=new_tally_datum,
    )
    builder.add_output(tally_output)
    builder.add_output(
        with_min_lovelace(
            pycardano.TransactionOutput(
                address=staking_address,
                amount=staking_utxo.output.amount
                - Value(multi_asset=asset_from_token(staking_vote_nft_tk, 1))
                - Value(multi_asset=asset_from_token(vote_permission_nft_tk, 1)),
                datum=new_staking_datum,
            ),
            context,
        )
    )

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    show_tx(signed_tx)
    return signed_tx


if __name__ == "__main__":
    fire.Fire(main)
