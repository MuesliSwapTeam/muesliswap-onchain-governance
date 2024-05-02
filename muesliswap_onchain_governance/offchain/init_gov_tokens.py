from fractions import Fraction

import fire

from muesliswap_onchain_governance.utils.network import show_tx, context
from opshin.ledger.api_v2 import (
    POSIXTime,
)
from opshin.std.fractions import Fraction as OnchainFraction
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

from .util import (
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
from ..utils import get_signing_info, ogmios_url, network, kupo_url
from ..utils.contracts import get_contract, get_ref_utxo, module_name
from ..utils.to_script_context import to_address, to_tx_out_ref

(_, vault_ft_policy_id, _) = get_contract(module_name(vault_ft), True)


def main(
    wallet: str = "creator",
    token_name: str = b"tMILK".hex(),
    amount: int = 1000000,
):
    # Load script info
    free_mint_script, free_mint_policy, _ = get_contract("free_mint", compressed=True)
    free_token = Token(
        policy_id=free_mint_policy.payload, token_name=bytes.fromhex(token_name)
    )

    payment_vkey, payment_skey, payment_address = get_signing_info(wallet)

    # Build the transaction
    builder = TransactionBuilder(context)
    builder.auxiliary_data = AuxiliaryData(
        data=AlonzoMetadata(
            metadata=Metadata({674: {"msg": ["Create Governance Token"]}})
        )
    )
    builder.add_input_address(payment_address)
    builder.add_minting_script(free_mint_script, Redeemer(Nothing()))
    builder.mint = asset_from_token(free_token, amount)

    # Sign the transaction
    signed_tx = builder.build_and_sign(
        signing_keys=[payment_skey],
        change_address=payment_address,
    )

    # Submit the transaction
    context.submit_tx(signed_tx)

    print(f"Created governance token")

    show_tx(signed_tx)

    return signed_tx


if __name__ == "__main__":
    fire.Fire(main)
