import peewee
import pycardano
from ..db_models import Block, TransactionOutput, TrackedTreasuryStates
from ..db_models.gov_state import TrackedGovStates
from ..util import FixedTxHashTransaction

from .gov_state import process_tx as process_gov_state_tx
from .staking import process_tx as process_staking_tx
from .tally import process_tx as process_tally_tx
from .licenses import process_tx as process_licenses_tx
from .treasury import process_tx as process_treasury_tx


def process_tx(
    tx: FixedTxHashTransaction,
    block: Block,
    block_index: int,
    tracked_gov_states: TrackedGovStates,
    tracked_treasury_states: TrackedTreasuryStates,
):
    """
    Process a transaction and update the database accordingly.
    """

    # mark all inputs to the transaction as spent
    spent_inputs = [
        (_input.transaction_id.payload.hex(), _input.index)
        for i, _input in enumerate(tx.transaction_body.inputs)
    ]
    TransactionOutput.update(spent_in_block=block).where(
        peewee.Tuple(
            TransactionOutput.transaction_hash, TransactionOutput.output_index
        ).in_(spent_inputs)
    ).execute()

    # model specific processing
    process_gov_state_tx(tx, block, block_index, tracked_gov_states)
    process_staking_tx(tx, block, block_index, tracked_gov_states)
    process_tally_tx(tx, block, block_index, tracked_gov_states)
    process_licenses_tx(tx, block, block_index, tracked_gov_states)
    process_treasury_tx(tx, block, block_index, tracked_treasury_states)
