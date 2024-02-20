import fire

from muesliswap_onchain_governance.utils.network import show_tx, context
from opshin.ledger.api_v2 import (
    POSIXTime,
)
from opshin.prelude import Token
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

from ..util import (
    token_from_string,
    asset_from_token,
    with_min_lovelace,
)
from muesliswap_onchain_governance.onchain.staking import (
    staking_vote_nft,
    staking,
    vault_ft,
)
from muesliswap_onchain_governance.onchain.tally import tally_auth_nft, tally
from muesliswap_onchain_governance.onchain.gov_state import gov_state_nft, gov_state
from ...utils import get_signing_info, ogmios_url, network, kupo_url
from ...utils.contracts import get_contract, get_ref_utxo, module_name
from ...utils.to_script_context import to_address, to_tx_out_ref


def main(
    wallet: str = "creator",
    governance_token: str = "bd976e131cfc3956b806967b06530e48c20ed5498b46a5eb836b61c2.744d494c4b",
    min_quorum: int = 1000,
    min_proposal_duration: POSIXTime = 1000,
):
    governance_token = token_from_string(governance_token)
    # Load script info
    (
        gov_state_nft_script,
        gov_state_nft_policy_id,
        _,
    ) = get_contract(module_name(gov_state_nft), True)
    gov_nft_ref_utxo = get_ref_utxo(gov_state_nft_script, context)
    (
        gov_state_script,
        gov_state_policy_id,
        gov_state_address,
    ) = get_contract(module_name(gov_state), True)
    (
        tally_script,
        tally_policy_id,
        tally_address,
    ) = get_contract(module_name(tally), True)
    (
        _,
        tally_auth_nft_policy_id,
        _,
    ) = get_contract(module_name(tally_auth_nft), True)
    (
        _,
        staking_vote_nft_policy_id,
        _,
    ) = get_contract(module_name(staking_vote_nft), True)
    (
        staking_script,
        staking_policy_id,
        staking_address,
    ) = get_contract(module_name(staking), True)
    (_, vault_ft_policy_id, _) = get_contract(module_name(vault_ft), True)

    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )

    # Select UTxO to define the governance thread ID
    utxos = context.utxos(payment_address)
    unique_utxo = utxos[0]

    # generate expected gov_nft name
    gov_nft_name = gov_state_nft.gov_state_nft_name(to_tx_out_ref(unique_utxo.input))
    gov_nft_token = Token(
        policy_id=gov_state_nft_policy_id.payload,
        token_name=gov_nft_name,
    )

    # generate redeemer for the gov nft
    gov_nft_redeemer = Redeemer(0)

    # Make the datum of the GovState
    gov_state_datum = gov_state.GovStateDatum(
        gov_state.GovStateParams(
            tally_address=to_address(tally_address),
            staking_address=to_address(staking_address),
            governance_token=governance_token,
            vault_ft_policy=vault_ft_policy_id.payload,
            min_quorum=min_quorum,
            min_proposal_duration=min_proposal_duration,
            gov_state_nft=gov_nft_token,
            tally_auth_nft_policy=tally_auth_nft_policy_id.payload,
            staking_vote_nft_policy=staking_vote_nft_policy_id.payload,
            latest_applied_proposal_id=gov_state.ALWAYS_EARLY_PROPOSAL_ID,
        ),
        last_proposal_id=gov_state.INITIAL_PROPOSAL_ID,
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Create Governance Thread"]}})
        )
    )
    builder.add_input(unique_utxo)
    builder.add_input_address(payment_address)
    builder.add_minting_script(
        gov_nft_ref_utxo or gov_state_nft_script,
        gov_nft_redeemer,
    )
    output = with_min_lovelace(
        TransactionOutput(
            address=gov_state_address,
            amount=Value(
                coin=2000000,
                multi_asset=asset_from_token(gov_nft_token, 1),
            ),
            datum=gov_state_datum,
        ),
        context,
    )
    builder.add_output(output)
    builder.mint = asset_from_token(gov_nft_token, 1)

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    print(f"Created governance thread with gov_nft_name: {gov_nft_name.hex()}")

    show_tx(signed_tx)


if __name__ == "__main__":
    fire.Fire(main)
