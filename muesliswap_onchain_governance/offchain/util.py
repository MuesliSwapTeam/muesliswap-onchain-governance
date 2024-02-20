from typing import List

import pycardano

from opshin.prelude import Token
from pycardano import MultiAsset, ScriptHash, Asset, AssetName, Value

GOV_STATE_NFT_TK_NAME = (
    "bc0a47f8459162152c33913f9d4e50d2340459ce4b6197761967d64368e0e50c"
)
TREASURER_STATE_NFT_TK_NAME = (
    "f0cb6462eb8a44c239c382506c38291413dd9a96c18bc0d079ea9b4d950d9f16"
)


def token_from_string(token: str) -> Token:
    if token == "lovelace":
        return Token(b"", b"")
    policy_id, token_name = token.split(".")
    return Token(
        policy_id=bytes.fromhex(policy_id),
        token_name=bytes.fromhex(token_name),
    )


def asset_from_token(token: Token, amount: int) -> MultiAsset:
    return MultiAsset(
        {ScriptHash(token.policy_id): Asset({AssetName(token.token_name): amount})}
    )


def with_min_lovelace(
    output: pycardano.TransactionOutput, context: pycardano.ChainContext
):
    min_lvl = pycardano.min_lovelace(context, output)
    output.amount.coin = max(output.amount.coin, min_lvl + 500000)
    return output


def sorted_utxos(txs: List[pycardano.UTxO]):
    return sorted(
        txs,
        key=lambda u: (u.input.transaction_id.payload, u.input.index),
    )


def amount_of_token_in_value(
    token: Token,
    value: Value,
) -> int:
    return value.multi_asset.get(ScriptHash(token.policy_id), {}).get(
        AssetName(token.token_name), 0
    )
