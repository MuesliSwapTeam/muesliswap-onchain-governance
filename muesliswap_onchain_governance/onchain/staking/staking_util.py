"""
Utils for the staking contracts. This is not a contract.
"""
from muesliswap_onchain_governance.onchain.util import *
from opshin.std.math import *


@dataclass
class AddVote(PlutusData):
    """
    Redeemer for the staking contract to add a vote to the tally.

    Adds a vote to the tally and tracks
    the participation in the staking state
    """

    CONSTR_ID = 1
    state_input_index: int
    state_output_index: int
    participation: Participation


@dataclass
class RetractVote(PlutusData):
    """
    Redeemer for the staking contract to retract a vote from the tally.

    Removes the vote from the tally and
    removes the participation from the staking state
    """

    CONSTR_ID = 2
    state_input_index: int
    state_output_index: int
    participation_index: int
    tally_input_index: int


@dataclass
class WithdrawFunds(PlutusData):
    """
    Redeemer for the staking contract to withdraw funds from the staking state.

    Removes funds from the staking state
    """

    CONSTR_ID = 3
    state_input_index: int
    # TODO allow Optional[BoxedInteger] to allow removing the state
    state_output_index: int


@dataclass
class AddFunds(PlutusData):
    """
    Adds funds to the staking state
    """

    CONSTR_ID = 4
    state_input_index: int
    state_output_index: int


@dataclass
class FilterOutdatedVotes(PlutusData):
    """
    Removes outdated participations
    """

    CONSTR_ID = 5
    state_input_index: int
    state_output_index: int


StakingRedeemer = Union[
    AddVote, RetractVote, WithdrawFunds, AddFunds, FilterOutdatedVotes
]


def construct_desired_output_staking_state(
    previous_state: StakingState, redeemer: StakingRedeemer, tx_info: TxInfo
) -> StakingState:
    if isinstance(redeemer, AddVote):
        # Ensure that list is only extended
        desired_next_state_participation = [
            redeemer.participation
        ] + previous_state.participations
    elif isinstance(redeemer, RetractVote):
        # Ensure that only one element is removed
        # And that the auth nft is unlocked == the tally contract approves the transaction
        desired_next_state_participation = remove_participation_at_index(
            previous_state.participations, redeemer.participation_index
        )
        assert token_present_in_output(
            previous_state.params.tally_auth_nft,
            tx_info.inputs[redeemer.tally_input_index].resolved,
        ), "Auth NFT was not spent in specified tally index input"
    elif isinstance(redeemer, FilterOutdatedVotes):
        desired_next_state_participation = [
            p
            for p in previous_state.participations
            if not vote_has_ended(p.end_time, tx_info.valid_range)
        ]
    elif isinstance(redeemer, WithdrawFunds) or isinstance(redeemer, AddFunds):
        desired_next_state_participation = previous_state.participations
    else:
        assert False, "Invalid redeemer"

    next_state = StakingState(
        desired_next_state_participation,
        previous_state.params,
    )

    return next_state


#### Permission NFT


@dataclass
class DelegatedAddVote(PlutusData):
    """
    Allows a third party to add a vote to the tally specified by the participation
    """

    CONSTR_ID = 1
    participation: Participation


@dataclass
class DelegatedRetractVote(PlutusData):
    """
    Allows a third party to retract a vote from the tally specified by the participation

    Note: One must not use the index here because the index might change when the staking state is updated
    """

    CONSTR_ID = 2
    participation: Participation


# Staking redeemers for which the user can give a third party the right to perform the operation
DelegatableStakingRedeemer = Union[DelegatedAddVote, DelegatedRetractVote]


@dataclass
class VotePermissionNFTParams(PlutusData):
    """
    Parameters for the permission NFT
    """

    CONSTR_ID = 1
    owner: Address
    redeemer: DelegatableStakingRedeemer


def vote_permission_nft_token_name(
    params: VotePermissionNFTParams,
) -> TokenName:
    """
    This is the exact same as the datum hash of the redeemer to aid looking up the datum in common chain indexers.
    """
    return blake2b_256(params.to_cbor())


def governance_weight_in_output(
    output: TxOut,
    governance_token: Token,
    vault_ft_policy: PolicyId,
    tally_end: ExtendedPOSIXTime,
) -> int:
    """
    Returns the weight of governance tokens in the output
    and also adds the weight of the governance tokens that are locked in the vault and will be unlocked after the end of the tally
    """
    governance_token_amount = amount_of_token_in_output(governance_token, output)
    valid_vault_tokens = 0
    if isinstance(tally_end, FinitePOSIXTime):
        tally_end_time = tally_end.time
        for tokenname, amount in output.value.get(
            vault_ft_policy, EMTPY_TOKENNAME_DICT
        ).items():
            if unsigned_int_from_bytes_big(tokenname) <= tally_end_time:
                valid_vault_tokens += amount
    return governance_token_amount + valid_vault_tokens
