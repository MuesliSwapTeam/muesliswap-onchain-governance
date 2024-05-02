import pycardano
from .to_db import (
    add_output,
    add_address,
    add_token,
    add_token_token,
    add_token,
    add_transaction,
)
from ..config import gov_state_nft_policy_id
from ..db_models import Block, TransactionOutput, Transaction
from ..db_models import gov_state as db_gov_state

from ...onchain.gov_state import gov_state as onchain_gov_state

import logging

from ...utils.from_script_context import from_address

_LOGGER = logging.getLogger(__name__)


def process_tx(
    tx: pycardano.Transaction,
    block: Block,
    block_index: int,
    tracked_gov_states: db_gov_state.TrackedGovStates,
):
    """
    Process a transaction and update the database accordingly.
    Updates the tracked_gov_states list with new or spent gov states
    """
    created_states = []
    for i, output in enumerate(tx.transaction_body.outputs):
        if not output.amount.multi_asset.get(gov_state_nft_policy_id):
            continue
        _LOGGER.info(f"Transaction contains gov state nft {tx.id.payload.hex()}")
        gov_state_output = add_output(
            output, i, tx.id.payload.hex(), block, block_index
        )
        try:
            _onchain_gov_state: onchain_gov_state.GovStateDatum = (
                onchain_gov_state.GovStateDatum.from_primitive(output.datum.data)
            )
        except Exception as e:
            _LOGGER.info(f"Invalid gov state parameters at {tx.id.payload.hex()}")
            continue
        gov_state_nft_name = list(
            output.amount.multi_asset[gov_state_nft_policy_id].keys()
        )[0]
        onchain_gov_state_params = _onchain_gov_state.params
        db_gov_state_params = db_gov_state.GovParams.get_or_create(
            tally_address=add_address(
                from_address(onchain_gov_state_params.tally_address)
            ),
            staking_address=add_address(
                from_address(onchain_gov_state_params.staking_address)
            ),
            governance_token=add_token_token(onchain_gov_state_params.governance_token),
            vault_ft_policy=onchain_gov_state_params.vault_ft_policy.hex(),
            min_quorum=onchain_gov_state_params.min_quorum,
            min_proposal_duration=onchain_gov_state_params.min_proposal_duration,
            gov_state_nft=add_token(
                gov_state_nft_policy_id,
                gov_state_nft_name,
            ),
            tally_auth_nft_policy=onchain_gov_state_params.tally_auth_nft_policy.hex(),
            staking_vote_nft_policy=onchain_gov_state_params.staking_vote_nft_policy.hex(),
            latest_applied_proposal_id=onchain_gov_state_params.latest_applied_proposal_id,
        )[0]
        _db_gov_state = db_gov_state.GovState.create(
            transaction_output=gov_state_output,
            gov_params=db_gov_state_params,
            last_proposal_id=_onchain_gov_state.last_proposal_id,
        )
        created_states.append(_db_gov_state)

        tracked_gov_states.append(_db_gov_state)

    spent_states = []
    # we don't need to bother checking the inputs if no output stake is created
    # there is no way to spend a gov state without creating one
    if created_states:
        for input in tx.transaction_body.inputs:
            _db_gov_state = (
                db_gov_state.GovState.select()
                .join(TransactionOutput)
                .where(
                    TransactionOutput.transaction_hash
                    == input.transaction_id.payload.hex(),
                    TransactionOutput.output_index == input.index,
                )
                .first()
            )
            if _db_gov_state is None:
                continue
            spent_states.append(_db_gov_state)

            tracked_gov_states.remove(_db_gov_state)
        # There may be multiple created states, but only one spent state
        for created_state in created_states:
            db_gov_state.GovUpgrade.create(
                transaction=add_transaction(tx.id.payload.hex(), block, block_index),
                prev_gov_state=spent_states[0] if spent_states else None,
                next_gov_state=created_state,
            )
