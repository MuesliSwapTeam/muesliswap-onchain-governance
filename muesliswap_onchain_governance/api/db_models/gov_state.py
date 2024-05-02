from typing import List

from .db import *


class GovParams(BaseModel):
    tally_address = ForeignKeyField(Address, backref="gov_states")
    staking_address = ForeignKeyField(Address, backref="gov_states")
    governance_token = ForeignKeyField(Token, backref="gov_states")
    vault_ft_policy = PolicyId()
    min_quorum = IntegerField()
    min_proposal_duration = IntegerField()
    gov_state_nft = ForeignKeyField(Token, backref="gov_states")
    tally_auth_nft_policy = PolicyId()
    staking_vote_nft_policy = PolicyId()
    latest_applied_proposal_id = IntegerField()


class GovState(OutputStateModel):
    """
    Mirrors the current status of the on-chain governance state
    """

    last_proposal_id = IntegerField()
    gov_params = ForeignKeyField(GovParams, backref="gov_states")


class GovUpgrade(TransActionModel):
    """
    Model the upgrade of the governance state
    If prev_gov_state is None, the upgrade is the creation of the governance state
    """

    prev_gov_state = ForeignKeyField(
        GovState, backref="gov_upgrades_prev", null=True, on_delete="CASCADE"
    )
    next_gov_state = ForeignKeyField(
        GovState, backref="gov_upgrades_next", on_delete="CASCADE"
    )


TrackedGovStates = List[GovState]
