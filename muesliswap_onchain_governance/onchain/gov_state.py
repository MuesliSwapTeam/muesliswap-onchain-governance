from opshin.prelude import *
from muesliswap_onchain_governance.onchain.util import *


@dataclass
class GovStateDatum(PlutusData):
    """
    Datum for the governance state
    """

    CONSTR_ID = 0
    governance_address: Address
    governance_token: Token
    min_quorum: int
    min_proposal_duration: POSIXTime
    gov_nft: Token
    auth_nft_policy: PolicyId
    stake_nft_policy: PolicyId
    last_proposal_id: ProposalId


@dataclass
class CreateNewTally(PlutusData):
    """
    Request to generate a new tally
    """

    CONSTR_ID = 0


@dataclass
class UpdateGovState(PlutusData):
    """
    Request to update a parameter in the GovStateDatum
    """

    CONSTR_ID = 1
    tally_index: int


GovStateRedeemer = Union[CreateNewTally, UpdateGovState]


def validate_new_tally(
    state: GovStateDatum, redeemer: CreateNewTally, context: ScriptContext
):
    """
    Validate a new tally proposal
    This ensures that the created proposal has the correct parameters and is created at the right address
    Further it ensures that the creator of the proposal locks/pays the correct amount of fee for creation
    """

    # TODO
    pass


def validate_update_gov_state(
    state: GovStateDatum, redeemer: UpdateGovState, context: ScriptContext
):
    """
    Validate an update to the governance state
    This ensures that the update is backed by a valid tally result at the governance address.
    """
    # TODO
    pass


def validator(
    state: GovStateDatum, redeemer: GovStateRedeemer, context: ScriptContext
) -> None:
    """
    GovState Contract.

    Ensures that new tally proposals are only submitted with the correct parameters
    defined in the governance state.
    The only other operation allowed is to update the governance state.
    """
    purpose = get_spending_purpose(context)
    # ensure that only one gov state is spent at any time
    gov_state_address = own_spent_utxo(context.tx_info.inputs, purpose).address
    assert (
        sum(
            [
                1
                for i in context.tx_info.inputs
                if i.resolved.address == gov_state_address
            ]
        )
        == 1
    ), "Trying to spend more than one governance state"
    if isinstance(redeemer, CreateNewTally):
        validate_new_tally(state, redeemer, context)
    elif isinstance(redeemer, UpdateGovState):
        validate_update_gov_state(state, redeemer, context)
    else:
        assert False, "Invalid redeemer"
