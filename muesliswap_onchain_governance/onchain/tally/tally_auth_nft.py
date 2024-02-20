from opshin.prelude import *

from muesliswap_onchain_governance.onchain.util import *


@dataclass
class AuthRedeemer(PlutusData):
    """
    Redeemer for the auth NFT policy
    """

    CONSTR_ID = 0
    spent_utxo_index: int
    governance_nft_name: TokenName


def validator(
    governance_nft_policy: PolicyId, redeemer: AuthRedeemer, context: ScriptContext
) -> None:
    """
    Authentication NFT policy.
    Ensures that the name of the resulting NFT matches the governance NFT
    that is being spent in the given transaction.
    The policy is parameterized by the policy id of the governance NFT.
    """
    auth_policy_id = get_minting_purpose(context).policy_id

    # Check that
    # 1. the governance NFT is being spent
    # 2. the tokenname is the name of the spent governance NFT

    spent_input = context.tx_info.inputs[redeemer.spent_utxo_index].resolved
    required_token_name = redeemer.governance_nft_name
    assert (
        spent_input.value[governance_nft_policy][required_token_name] == 1
    ), "Governance NFT is not being spent"

    check_mint_exactly_one_with_name(
        context.tx_info.mint, auth_policy_id, required_token_name
    )
