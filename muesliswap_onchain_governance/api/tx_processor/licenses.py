import datetime

import pycardano

from . import from_db
from .to_db import (
    add_address,
    add_token,
    add_transaction,
    add_output,
)
from ..config import licenses_policy_id
from ..db_models import (
    Block,
    TransactionOutput,
    Transaction,
    TallyState,
    TreasurerState,
)
from ..db_models import (
    TrackedGovStates,
)
from ..db_models.licenses import LicenseMint, LicenseOutput

from ...onchain.licenses import licenses as onchain_licenses

import logging


_LOGGER = logging.getLogger(__name__)


def process_tx(
    tx: pycardano.Transaction,
    block: Block,
    block_index: int,
    tracked_gov_states: TrackedGovStates,
):
    """
    Process a transaction and update the database accordingly.
    """
    # add outputs if they contain licenses
    for i, output in enumerate(tx.transaction_body.outputs):
        if output.amount.multi_asset.get(licenses_policy_id, {}):
            db_output = add_output(output, i, tx.id.payload.hex(), block, block_index)
            for license_token_name in output.amount.multi_asset.get(
                licenses_policy_id, {}
            ).keys():
                # we can find the tally input here
                LicenseOutput.create(
                    output=db_output,
                    license_nft=add_token(licenses_policy_id, license_token_name),
                )
    # add mints if they contain licenses
    license_mint = (
        tx.transaction_body.mint.get(licenses_policy_id)
        if tx.transaction_body.mint
        else None
    )
    if not license_mint:
        return
    license_token_name, license_mint_amount = list(license_mint.items())[0]

    receiver = None
    for i, output in enumerate(tx.transaction_body.outputs):
        if (
            output.amount.multi_asset.get(licenses_policy_id, {}).get(
                license_token_name, 0
            )
            > 0
        ):
            receiver = output.address
            break
    release_license_redeemer = None
    for redeemer in tx.transaction_witness_set.redeemer:
        if redeemer.tag != pycardano.RedeemerTag.MINT.value:
            continue
        if (
            sorted(tx.transaction_body.mint, key=lambda x: x.payload)[redeemer.index]
            != licenses_policy_id
        ):
            continue
        try:
            release_license_redeemer: onchain_licenses.ReleaseLicenses = (
                onchain_licenses.ReleaseLicenses.from_primitive(redeemer.data.data)
            )
        except Exception as e:
            _LOGGER.debug(f"Mint was executed with invalid redeemer")
            continue
    # we can find the tally input here
    if release_license_redeemer is not None:
        input = sorted(
            tx.transaction_body.reference_inputs,
            key=lambda x: (x.transaction_hash.payload, x.index),
        )[release_license_redeemer.tally_input_index]
        tally_state = (
            TallyState.select()
            .join(TransactionOutput)
            .where(
                TransactionOutput.transaction_hash
                == input.transaction_id.payload.hex(),
                TransactionOutput.output_index == input.index,
            )
            .first()
        )
    if receiver is not None and tally_state is not None:
        LicenseMint.create(
            transaction=add_transaction(tx.id.payload.hex(), block, block_index),
            receiver=add_address(receiver),
            used_tally_state=tally_state,
            minted_amount=license_mint_amount,
            license_nft=add_token(licenses_policy_id, license_token_name),
            expiration_date=datetime.datetime.fromtimestamp(
                int.from_bytes(license_token_name.payload[3:], "big")
            ),
            tally_proposal_id=int.from_bytes(license_token_name.payload[:3], "big"),
        )
