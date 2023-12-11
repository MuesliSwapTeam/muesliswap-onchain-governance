from opshin.prelude import *

from muesliswap_onchain_governance.onchain.util import *


@dataclass
class BoxedInt(PlutusData):
    """
    Boxed Int
    """

    CONSTR_ID = 0
    value: int


OptionalInt = Union[BoxedInt, Nothing]


@dataclass
class AddVote(PlutusData):
    """
    Adds a vote to the tally
    """

    CONSTR_ID = 1
    proposal_index: int
    weight: int
    staking_input_index: OptionalInt
    staking_output_index: int


@dataclass
class RetractVote(PlutusData):
    """
    Adds a vote to the tally
    """

    CONSTR_ID = 2
    proposal_index: int
    weight: int
    staking_input_index: int
    staking_output_index: int


TallyAction = Union[AddVote, RetractVote]


def validator(tally: TallyState, redeemer: TallyAction, context: ScriptContext) -> None:
    """
    Tally State tracker
    Ensures that tallys are correctly updated based on staked funds.
    """
    pass
