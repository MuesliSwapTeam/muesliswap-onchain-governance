"""
The main file containing the logic for starting the querier.
The querier syncs with the blockchain, listening for new blocks and updating the database accordingly.
"""
import logging

import fire
from muesliswap_onchain_governance.api.tx_processor import process_tx

from ..utils.network import ogmios_url
from . import ogmios
from .db_models import Block, GovState, TransactionOutput, TreasurerState

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


def main(rollback_to_slot: int = None, debug_sql: bool = False):
    """
    Start the querier.
    """
    if debug_sql:
        logger = logging.getLogger("peewee")
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)

    _LOGGER.info("Starting the querier")
    if rollback_to_slot is not None:
        Block.delete().where(Block.slot > rollback_to_slot).execute()
    sync_blocks = [
        Block.select().order_by(Block.slot.desc()).first(),
        Block.select().order_by(Block.slot.desc()).offset(1).first(),
        Block.select().order_by(Block.slot.desc()).offset(5).first(),
        Block.select().order_by(Block.slot.desc()).offset(50).first(),
        Block.select().order_by(Block.slot.desc()).offset(1000).first(),
    ]

    tracked_gov_states = []
    tracked_treasury_states = []

    for operation in ogmios.OgmiosIterator(ogmios_url).iterate_blocks(
        [
            ogmios.Point(slot=block.slot, id=block.hash)
            for block in sync_blocks
            if block is not None
        ]
    ):
        if isinstance(operation, ogmios.Rollback):
            if isinstance(operation.tip, ogmios.Origin):
                _LOGGER.info("Rollback to origin")
                Block.delete().execute()
                continue
            else:
                _LOGGER.info("Rollback to tip", operation.tip)
                Block.delete().where(Block.slot > operation.tip.slot).execute()
                # At least one Rollback is executed once after each restart, so we can be sure this is initialized correctly
                tracked_gov_states = list(
                    GovState.select()
                    .join(TransactionOutput)
                    .where(TransactionOutput.spent_in_block.is_null())
                )
                tracked_treasury_states = list(
                    TreasurerState.select()
                    .join(TransactionOutput)
                    .where(TransactionOutput.spent_in_block.is_null())
                )
                continue
        else:
            block = ogmios.tip_from_block(operation.block)
            db_block = Block(hash=block.id, slot=block.slot, height=block.height)
            db_block.save()
            try:
                for i, tx in enumerate(ogmios.txs_from_block(operation.block)):
                    process_tx(
                        tx, db_block, i, tracked_gov_states, tracked_treasury_states
                    )
            except Exception as e:
                _LOGGER.info(f"Error processing block {block.id}: {e}")
                db_block.delete_instance()
                raise


if __name__ == "__main__":
    fire.Fire(main)
