"""
Consumer of the tally states.
Releases specified funds to the specified address if the tally is successful.
"""


from muesliswap_onchain_governance.onchain.treasury.util import *


@dataclass
class FundPayoutParams(PlutusData):
    """
    Redeemer for the value store contract to issue a payout of funds.
    """

    CONSTR_ID = 3
    treasurer_index: int


ValueStoreRedeemer = FundPayoutParams


def validator(
    value_store_state: ValueStoreState,
    redeemer: ValueStoreRedeemer,
    context: ScriptContext,
) -> None:
    """
    Value store validator. Ensures to only release funds if the treasurer approves the transaction, i.e. is spent in it.
    """
    treasurer_input = context.tx_info.inputs[redeemer.treasurer_index].resolved
    assert token_present_in_output(
        value_store_state.treasurer_nft, treasurer_input
    ), "Unique treasurer NFT is not present in the treasurer input"
