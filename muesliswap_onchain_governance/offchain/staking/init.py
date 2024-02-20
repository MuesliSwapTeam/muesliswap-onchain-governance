import fire

from muesliswap_onchain_governance.utils.network import show_tx, context
from opshin.ledger.api_v2 import (
    POSIXTime,
)
from opshin.prelude import Token
from pycardano import (
    TransactionBuilder,
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
    GOV_STATE_NFT_TK_NAME,
)
from muesliswap_onchain_governance.onchain.staking import staking, vault_ft
from muesliswap_onchain_governance.onchain.tally import tally_auth_nft
from ...utils import get_signing_info, ogmios_url, network, kupo_url
from ...utils.contracts import get_contract, get_ref_utxo, module_name
from ...utils.to_script_context import to_address, to_tx_out_ref


def main(
    wallet: str = "creator",
    governance_token: str = "bd976e131cfc3956b806967b06530e48c20ed5498b46a5eb836b61c2.744d494c4b",
    locked_amount: int = 1000,
    tally_auth_nft_tk_name: str = GOV_STATE_NFT_TK_NAME,
):
    governance_token = token_from_string(governance_token)

    # Load script info
    (
        staking_script,
        _,
        staking_address,
    ) = get_contract(module_name(staking), True)
    (_, tally_auth_nft_policy_id, _) = get_contract(module_name(tally_auth_nft), True)
    (_, vault_ft_policy_id, _) = get_contract(module_name(vault_ft), True)

    tally_auth_nft_tk = Token(
        tally_auth_nft_policy_id.payload, bytes.fromhex(tally_auth_nft_tk_name)
    )

    # Get payment address
    payment_vkey, payment_skey, payment_address = get_signing_info(
        wallet, network=network
    )

    # Make the datum of the GovState
    staking_datum = staking.StakingState(
        [],
        staking.StakingParams(
            owner=to_address(payment_address),
            governance_token=governance_token,
            tally_auth_nft=tally_auth_nft_tk,
            vault_ft_policy=vault_ft_policy_id.payload,
        ),
    )

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(payment_address)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Create Staking Position"]}})
        )
    )
    output = TransactionOutput(
        address=staking_address,
        amount=Value(
            coin=2000000,
            multi_asset=asset_from_token(governance_token, locked_amount),
        ),
        datum=staking_datum,
    )
    builder.add_output(with_min_lovelace(output, context))

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    show_tx(signed_tx)


if __name__ == "__main__":
    fire.Fire(main)
