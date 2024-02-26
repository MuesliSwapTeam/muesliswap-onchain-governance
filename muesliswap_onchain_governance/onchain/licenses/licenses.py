"""
The license NFT contract.

Consumer of the tally states.
Releases license with limited validity to the specified address if the tally is successful.
Tallys are expected to have infinite validity and do not need to be finished for releasing licenses.
However the quorum must be reached.

Outputs of this contract may go to:
- The winning address of the referenced address in the winning tally

Reference inputs:
- tally/tally (1, referencing a winning proposal that indicates a governance upgrade)

NFTs that the outputs may hold:
- licenses/licenses (previously minted plus the own minted one)

It is not allowed to mint several license NFTs with distinct names in a single transaction but well allowed to mint
several licenses of the same name (i.e. expiry date).
"""
from opshin.std.math import *
from muesliswap_onchain_governance.onchain.util import *


@dataclass
class ReleaseLicenses(PlutusData):
    CONSTR_ID = 2
    license_name: TokenName
    release_index: int
    # the index of the reference input with the tally
    tally_input_index: int


@dataclass
class LicenseReleaseParams(PlutusData):
    """
    VOTE OUTCOME
    A possible vote outcome specifying what batcher will receive liceneses.
    """

    CONSTR_ID = 101
    address: Address
    datum: OutputDatum
    # how long into the future the license is valid
    future_validity: POSIXTime


def validator(
    auth_nft: Token, redeemer: ReleaseLicenses, context: ScriptContext
) -> None:
    """
    Check that liceneses are released to the specified address with limited validity.
    """
    tx_info = context.tx_info
    purpose = get_minting_purpose(context)

    winning_tally = winning_tally_result(
        redeemer.tally_input_index, auth_nft, tx_info, ALWAYS_EARLY_PROPOSAL_ID, False
    )
    winning_tally_params: LicenseReleaseParams = winning_tally.winning_proposal

    # check that the correct license is minted
    minted_amount = 0
    for tkname, tkamount in tx_info.mint[purpose.policy_id].items():
        assert tkname == redeemer.license_name, "License minted with wrong name"
        minted_amount += tkamount

    # check that the license is released to the specified address
    license = Token(purpose.policy_id, redeemer.license_name)
    total_amount_sent_out = all_tokens_locked_at_address_with_datum(
        tx_info.outputs,
        winning_tally_params.address,
        license,
        winning_tally_params.datum,
    )
    assert (
        total_amount_sent_out == minted_amount
    ), "License not released to the specified address with specified datum"

    # check that the license has a valid name (not minted too late)
    license_posix = unsigned_int_from_bytes_big(redeemer.license_name)
    transaction_validity_posix = tx_info.valid_range.lower_bound.limit
    assert isinstance(
        transaction_validity_posix, FinitePOSIXTime
    ), "Transaction validity lower bound must be finite"
    latest_allowed_license_posix = (
        transaction_validity_posix.time + winning_tally_params.future_validity
    )
    assert license_posix <= latest_allowed_license_posix, "License minted too late"
