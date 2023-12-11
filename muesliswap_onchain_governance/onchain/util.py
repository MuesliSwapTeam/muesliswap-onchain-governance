from opshin.prelude import *

ProposalId = int


def increment_proposal_id(id: ProposalId) -> ProposalId:
    return id + 1


def get_minting_purpose(context: ScriptContext) -> Minting:
    purpose = context.purpose
    assert isinstance(purpose, Minting)
    return purpose


def get_spending_purpose(context: ScriptContext) -> Spending:
    purpose = context.purpose
    assert isinstance(purpose, Spending)
    return purpose


@dataclass
class TallyState(PlutusData):
    """
    Tracks the tally of a proposal
    """

    CONSTR_ID = 0
    quorum: int
    votes: List[int]
    proposals: List[Anything]
    end_time: ExtendedPOSIXTime
    proposal_id: ProposalId
    auth_nft: Token
    stake_nft: PolicyId


def check_mint_exactly_one_with_name(
    mint: Value, policy_id: PolicyId, required_token_name: TokenName
) -> None:
    for minted_policy, d in mint.items():
        if minted_policy == policy_id:
            for minted_token_name, amount in d.items():
                assert (
                    minted_token_name == required_token_name
                ), "Token name is not the required name"
                assert amount == 1, "More than one token minted"
