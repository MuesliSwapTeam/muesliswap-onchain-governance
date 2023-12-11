from opshin.prelude import *

from muesliswap_onchain_governance.onchain.util import *


@dataclass
class Participation(PlutusData):
    """
    Tracks the participation of a voter
    """

    CONSTR_ID = 0
    weight: int
    auth_nft: Token
    id: ProposalId
    end_time: ExtendedPOSIXTime


@dataclass
class StakingDatum(PlutusData):
    """
    Tracks the amount of tokens staked by a user
    and the voters participation
    """

    CONSTR_ID = 0
    participations: List[Participation]
    owner: Address


@dataclass
class AddVote(PlutusData):
    """
    Adds a vote to the tally and tracks
    the participation in the staking state
    """

    CONSTR_ID = 1


@dataclass
class RetractVote(PlutusData):
    """
    Removes the vote from the tally and
    removes the participation from the staking state
    """

    CONSTR_ID = 2


@dataclass
class WithdrawFunds(PlutusData):
    """
    Removes funds from the staking state
    """

    CONSTR_ID = 3


@dataclass
class AddFunds(PlutusData):
    """
    Adds funds to the staking state
    """

    CONSTR_ID = 4


StakingRedeemer = Union[AddVote, RetractVote, WithdrawFunds, AddFunds]


def validator(
    state: StakingDatum, redeemer: StakingRedeemer, context: ScriptContext
) -> None:
    """
    Staking Contract
    Locks user funds and tracks participation in the governance.
    Funds can only be withdrawn after the proposals that the fund participate in have ended.
    Until the end of participating proposals, the user can only withdraw so many tokens that all proposals are still backed (max of participating funds).
    The user may add or retract votes at any time, with weight up to the locked tokens or participating tokens respectively.

    Note that the staking contract is not aware of the existance of the governance state.
    This is why a vote participation is only valid when accompanied by the the correct stake authentication NFT.
    """
    pass
