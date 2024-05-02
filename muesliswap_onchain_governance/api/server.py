import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Query, FastAPI
from fastapi.responses import ORJSONResponse
from starlette.responses import Response
from fastapi_cache import FastAPICache, Coder
from fastapi_cache.decorator import cache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi.middleware.cors import CORSMiddleware
from gelidum import freeze

from muesliswap_onchain_governance.api.db_models import db
from muesliswap_onchain_governance.api.db_queries import (
    gov_state,
    staking,
    tally,
    treasury,
)

# logger setup
_LOGGER = logging.getLogger(__name__)


def DashingQuery(convert_underscores=True, **kwargs) -> Query:
    """
    This class enables "convert underscores" by default, allowing parameter names
    with underscores to be accessed via hypehenated versions
    """
    query = Query(**kwargs)
    query.convert_underscores = convert_underscores
    return query


app = FastAPI(
    default_response_class=ORJSONResponse,
    title="MuesliSwap Governance API.",
    description="The MuesliSwap Governance API provides access to on-chain data for the MuesliSwap Onchain Governance System.",
    version="0.0.1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoCoder(Coder):
    @classmethod
    def encode(cls, value: Any) -> str:
        return value

    @classmethod
    def decode(cls, value: str) -> Any:
        return value


@asynccontextmanager
async def startup():
    # For now in memory, but we can use redis or other backends later
    FastAPICache.init(
        InMemoryBackend(),
        expire=20,
        coder=NoCoder,
    )
    yield


def add_cachecontrol(response: Response, max_age: int, directive: str = "public"):
    # see https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    # and https://fastapi.tiangolo.com/advanced/response-headers/
    response.headers["Cache-Control"] = f"{directive}, max-age={max_age}"


def add_jsoncontenttype(response: Response):
    # see https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    # and https://fastapi.tiangolo.com/advanced/response-headers/
    response.headers["Content-Type"] = f"application/json"


#################################################################################################
#                                            Endpoints                                          #
#################################################################################################

PolicyIdQuery = DashingQuery(
    description="Policy ID of a token",
    examples=["", "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb"],
    # TODO add validation
)
TokenNameQuery = DashingQuery(
    description="Hex encoded name of a token",
    examples=["", "4d494c4b7632"],
    # TODO add validation
)
AsBaseQuery = DashingQuery(
    description="Token that should be used as base",
    examples=["from", "to"],
    # TODO add validation
)
IncludeTradesQuery = DashingQuery(
    description="Whether or not to include the last trades data",
    examples=["true", "false"],
    # TODO add validation
)
IncludeAdaPricesQuery = DashingQuery(
    description="Whether or not to include the ada price data",
    examples=["true", "false"],
    # TODO add validation
)
VerifiedQuery = DashingQuery(
    description="Filter for only verified tokens",
    examples=["true", "false", "1", "0"],
    # TODO add validation
)
PubkeyHashQuery = DashingQuery(
    description="Pubkeyhash of a wallet",
    examples=["dcbc64ce3cc4aeac225a45dd67dfc3717f732f6303556efb6dd8024f"],
    # TODO add validation
)
StakekeyHashQuery = DashingQuery(
    description="Stake key hash of a wallet",
    examples=["dcbc64ce3cc4aeac225a45dd67dfc3717f732f6303556efb6dd8024f"],
    # TODO add validation
)
PubkeyHashesQuery = DashingQuery(
    description="Stake key hash of a wallet",
    examples=[
        "",
        "dcbc64ce3cc4aeac225a45dd67dfc3717f732f6303556efb6dd8024f,dcbc64ce3cc4aeac225a45dd67dfc3717f732f6303556efb6dd8024f",
    ],
    # TODO add validation
)
WalletQuery = DashingQuery(
    description="Wallet address in hex",
    examples=[
        "01dcbc64ce3cc4aeac225a45dd67dfc3717f732f6303556efb6dd8024f0420b0d045f11e8a66319f9d19ffcba35aa9fee0164014776a1f7c95"
    ],
    # TODO add validation
)
AddressQuery = DashingQuery(
    description="Wallet address in bech32",
    examples=[
        "addr1q8wtcexw8nz2atpztfza6e7lcdch7ue0vvp42mhmdhvqyncyyzcdq303r69xvvvln5vlljart25lacqkgq28w6sl0j2skvlxf4"
    ],
    # TODO add validation
)
ProviderQuery = DashingQuery(
    description="Provider name",
    examples=["muesliswap", "minswap", "vyfi"],
    # TODO add validation
)
TokenQuery = DashingQuery(
    description="Toke name in hex",
    examples=[
        ".",
        "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb.4d494c4b7632",
    ],
    # TODO add validation
)
AssetIdentifierQuery = DashingQuery(
    description="Asset identifier in hex: Concatenation of the policy_id and hex-encoded asset_name",
    examples=[
        "",
        "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb4d494c4b7632",
    ],
    # TODO add validation
)
TransactionHashQuery = DashingQuery(
    description="Transaction hash",
    examples=["6804edf9712d2b619edb6ac86861fe93a730693183a262b165fcc1ba1bc99cad"],
    # TODO add validation
)
TransactionIdQuery = DashingQuery(
    description="Transaction id",
    examples=[0, 1, 2],
    # TODO add validation
)


@app.get("/api/v1/health")
def health():
    last_block = db.Block.select().order_by(db.Block.slot.desc()).first()
    return ORJSONResponse(
        {
            "status": "ok" if last_block else "nok",
            "last_block": {
                "slot": last_block.slot,
                "height": last_block.height,
                "hash": last_block.hash,
            }
            if last_block
            else None,
        }
    )


@app.get("/api/v1/staking/positions")
def staking_positions(
    wallet: str = WalletQuery,
):
    """
    Get the currently open staking positions for a wallet.
    """
    return ORJSONResponse(staking.query_staking_positions_per_wallet(wallet))


@app.get("/api/v1/staking/history")
def staking_history(
    wallet: str = WalletQuery,
):
    """
    Get the staking history for a wallet.
    """
    return ORJSONResponse(staking.query_staking_history_per_wallet(wallet))


@app.get("/api/v1/tallies")
def tallies(
    open: bool = DashingQuery(
        description="Show open tallies",
        examples=["true", "false", "1", "0"],
    ),
    closed: bool = DashingQuery(
        description="Show closed tallies",
        examples=["true", "false", "1", "0"],
    ),
):
    """
    Get all open tallies
    """
    return ORJSONResponse(tally.query_tallies(closed, open))


@app.get("/api/v1/tallies/tally_detail")
def tally_detail(
    tally_auth_nft: str = DashingQuery(
        description="Tally Auth NFT",
        examples=[
            "471b0b6f3fab69f9c6e8c1c1389782a410a8689d97e22a22ac24b30f.bc0a47f8459162152c33913f9d4e50d2340459ce4b6197761967d64368e0e50c"
        ],
    ),
    tally_proposal_id: int = DashingQuery(
        description="Tally Proposal ID",
        examples=[0, 1, 2],
    ),
):
    """
    Get details for a specific tally
    """
    return ORJSONResponse(
        tally.query_tally_details_by_auth_nft_proposal_id(
            tally_auth_nft, tally_proposal_id
        )
    )


@app.get("/api/v1/tallies/tally_votes")
def tally_votes(
    tally_auth_nft: str = DashingQuery(
        description="Tally Auth NFT",
        examples=[
            "471b0b6f3fab69f9c6e8c1c1389782a410a8689d97e22a22ac24b30f.bc0a47f8459162152c33913f9d4e50d2340459ce4b6197761967d64368e0e50c"
        ],
    ),
    tally_proposal_id: int = DashingQuery(
        description="Tally Proposal ID",
        examples=[0, 1, 2],
    ),
):
    """
    Get votes for a specific tally
    """
    return ORJSONResponse(
        tally.query_all_user_votes_for_tally(tally_auth_nft, tally_proposal_id)
    )


@app.get("/api/v1/treasury/funds")
def treasury_funds():
    """
    Get the funds in the current treasury
    """
    return ORJSONResponse(treasury.query_current_treasury_funds())


@app.get("/api/v1/treasury/history")
def treasury_history():
    """
    Get the deposits, payouts and other operations on the treasury
    """
    return ORJSONResponse(treasury.query_treasury_history())


@app.get("/api/v1/treasury/chart")
def treasury_historical_funds():
    """
    Get the accumulated funds in treasury over time
    """
    return ORJSONResponse(treasury.query_historical_treasury_funds())


@app.get("/api/v1/gov/state")
def current_gov_state():
    """
    Get the current state of the governance system
    """
    return ORJSONResponse(gov_state.query_current_gov_state())
