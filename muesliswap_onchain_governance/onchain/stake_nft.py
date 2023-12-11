from opshin.prelude import *

from muesliswap_onchain_governance.onchain.util import *


@dataclass
class StakeAuthRedeemer(PlutusData):
    """
    Redeemer for the stake authentication NFT
    """

    CONSTR_ID = 0
    tally_input_index: int
    tally_output_index: int
    vote_index: int


def stake_auth_nft_name(
    vote_index: int, weight: int, tally_input_state: TallyState
) -> TokenName:
    return (
        f"{vote_index}|{weight}|{tally_input_state.proposal_id}|".encode()
        + tally_input_state.auth_nft.token_name
        + tally_input_state.auth_nft.policy_id
    )


def validator(
    governance_address: Address, redeemer: StakeAuthRedeemer, context: ScriptContext
) -> None:
    """
    Stake Authentication NFT
    This NFT authenticates that the user participated correctly in a governance proposal,
    i.e. a Staking Participation is only valid if accompanied by the matching NFT created by
    sha256(vote_index + vote_weight + proposalid + authnftname + authnftpolicyid).
    """
    purpose = get_minting_purpose(context)
    tx_info = context.tx_info

    tally_input = tx_info.inputs[redeemer.tally_output_index].resolved
    assert (
        tally_input.address == governance_address
    ), "Tally input is not the governance address"
    tally_input_state: TallyState = resolve_datum_unsafe(tally_input, tx_info)

    tally_output = tx_info.outputs[redeemer.tally_output_index]
    assert (
        tally_output.address == governance_address
    ), "Tally output is not the governance address"
    tally_output_state: TallyState = resolve_datum_unsafe(tally_output, tx_info)

    vote_index = redeemer.vote_index
    weight = (
        tally_output_state.votes[vote_index]
        - tally_input_state.votes[redeemer.vote_index]
    )
    desired_nft_name = stake_auth_nft_name(vote_index, weight, tally_input_state)

    check_mint_exactly_one_with_name(
        context.tx_info.mint, desired_nft_name, desired_nft_name
    )
