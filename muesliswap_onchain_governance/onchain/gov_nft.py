from opshin.prelude import *
from opshin.std.builtins import *

from muesliswap_onchain_governance.onchain.util import *


def gov_nft_name(spent_utxo: TxOutRef) -> TokenName:
    return sha2_256(f"{spent_utxo.idx}".encode() + spent_utxo.id.tx_id)


def validator(unique_utxo_index: int, context: ScriptContext) -> None:
    """
    One-shot minting policy. Ensures that the name of the resulting NFT is unique,
    being the hash of a consumed UTxO.
    """
    policy_id = get_minting_purpose(context).policy_id

    # Check that
    # 1. only one token of the own policy id is minted
    # 2. the tokenname is the hash of the spent UTxO indicated by the redeemer

    spent_input = context.tx_info.inputs[unique_utxo_index].out_ref
    required_token_name = gov_nft_name(spent_input)

    check_mint_exactly_one_with_name(
        context.tx_info.mint, policy_id, required_token_name
    )
