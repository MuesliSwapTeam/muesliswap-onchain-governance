import json
import time
import logging
from dataclasses import dataclass

import pycardano
import websocket

from muesliswap_onchain_governance.api.config import (
    start_block_slot,
    start_block_hash,
)
from muesliswap_onchain_governance.api.util import FixedTxHashTransaction

_LOGGER = logging.getLogger(__name__)

# this is the v6 format
TEMPLATE = {
    "jsonrpc": "2.0",
}

NEXT_BLOCK = TEMPLATE.copy()
NEXT_BLOCK["method"] = "nextBlock"
NEXT_BLOCK = json.dumps(NEXT_BLOCK)


@dataclass
class Point:
    slot: int
    id: str


@dataclass
class Tip:
    slot: int
    id: str
    height: int


class Origin:
    pass


@dataclass
class Rollforward:
    tip: Tip
    block: dict


@dataclass
class Rollback:
    tip: Point | Origin


NextBlockResult = Rollforward | Rollback


class OgmiosIterator:
    def __init__(self, ogmios_url: str):
        self.ogmios_url = ogmios_url
        self.ws = websocket.WebSocket()
        self.ws.connect(self.ogmios_url)

    def _init_connection(self, start_points: list[Point]):
        data = TEMPLATE.copy()
        data["method"] = "findIntersection"
        data["params"] = {
            "points": [{"slot": p.slot, "id": p.id} for p in start_points]
            + [{"slot": start_block_slot, "id": start_block_hash}]
            + ["origin"]
        }

        self.ws.send(json.dumps(data))
        # we send the origin so we will always find an intersection
        print(self.ws.recv())

    def iterate_blocks(self, start_points: list[Point]):
        self._init_connection(start_points)
        # we want to always keep 100 blocks in queue to avoid waiting for node
        for _ in range(100):
            self.ws.send(NEXT_BLOCK)
        while True:
            resp = json.loads(self.ws.recv())
            result = resp["result"]
            if result["direction"] == "forward":
                yield Rollforward(
                    tip=Tip(**result["tip"]),
                    block=result["block"],
                )
            else:
                yield Rollback(
                    tip=Point(**result["point"])
                    if "origin" != result["point"]
                    else Origin(),
                )
            self.ws.send(NEXT_BLOCK)


def tip_from_block(block: dict) -> Tip:
    return Tip(
        slot=block.get("slot", block["height"]),
        id=block["id"],
        height=block["height"],
    )


def txs_from_block(block: dict) -> list[FixedTxHashTransaction]:
    if block["type"] == "ebb":
        return []
    txs_transformed = []
    for tx in block["transactions"]:
        try:
            txs_transformed.append(
                FixedTxHashTransaction(
                    transaction=pycardano.Transaction.from_cbor(tx["cbor"]),
                    hash=tx["id"],
                )
            )
        except KeyError as e:
            raise ValueError(
                f"Error parsing transactions in block: {e}, make sure that --include-cbor is set as flag when running ogmios"
            ) from e
        except pycardano.DeserializeException as e:
            if "pycardano.certificate" in str(e):
                _LOGGER.info(
                    "Ignoring transaction with a certificate that is not supported by pycardano"
                )
                continue
            print(tx)
            raise ValueError(f"Error parsing transactions in block: {e}") from e
        except ValueError as e:
            if "2 is not a valid Network" in str(e):
                _LOGGER.info(
                    "Ignoring transaction with Byron address, not supported by pycardano"
                )
                continue
            print(tx)
            raise ValueError(f"Error parsing transactions in block: {e}") from e
        except Exception as e:
            print(tx)
            raise ValueError(f"Error parsing transactions in block: {e}") from e
    return txs_transformed
