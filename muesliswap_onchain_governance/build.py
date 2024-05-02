import datetime
import subprocess
import sys
from pathlib import Path
from typing import Union

import fire
from uplc.ast import PlutusByteString, plutus_cbor_dumps

import pycardano
from opshin.ledger.api_v2 import FinitePOSIXTime
from opshin.prelude import Token

from muesliswap_onchain_governance.onchain import free_mint
from .utils.to_script_context import to_address
from .utils.contracts import get_contract, module_name
from .utils.keys import get_address

from muesliswap_onchain_governance.onchain.staking import (
    vote_permission_nft,
    staking_vote_nft,
    staking,
    vault_ft,
)
from muesliswap_onchain_governance.onchain.tally import tally_auth_nft, tally
from muesliswap_onchain_governance.onchain.gov_state import gov_state_nft, gov_state
from muesliswap_onchain_governance.onchain.treasury import (
    treasurer,
    value_store,
    treasurer_nft,
)
from muesliswap_onchain_governance.onchain.licenses import licenses
from muesliswap_onchain_governance.onchain.simple_pool import (
    pool_nft,
    simple_pool,
    lp_token,
)


def build_compressed(
    type: str, script: Union[Path, str], cli_options=("--cf",), args=()
):
    script = Path(script)
    command = [
        sys.executable,
        "-m",
        "opshin",
        *cli_options,
        "build",
        type,
        script,
        *args,
        "--recursion-limit",
        "2000",
        "-O2",
    ]
    subprocess.run(command, check=True)

    built_contract = Path(f"build/{script.stem}/script.cbor")
    built_contract_compressed_cbor = Path(f"build/tmp.cbor")

    with built_contract_compressed_cbor.open("wb") as fp:
        subprocess.run(
            ["aiken", "uplc", "shrink", built_contract, "--cbor", "--hex"],
            stdout=fp,
            check=True,
        )

    subprocess.run(
        [
            sys.executable,
            "-m",
            "uplc",
            "build",
            "--from-cbor",
            built_contract_compressed_cbor,
            "-o",
            f"build/{script.stem}_compressed",
            "--recursion-limit",
            "2000",
        ]
    )


def token_from_token_string(token: str) -> Token:
    policy_id, token_name = token.split(".")
    return Token(bytes.fromhex(policy_id), bytes.fromhex(token_name))


def main(
    vault_contract_address: str = "addr1wyz9gd2m8y3q9ev5ee6tut6llxhxf34vp7a5tjm8d7q83gsu6r426",
    latest_vault_ft_mint_posix_time: int = int(
        datetime.datetime(2024, 6, 30).timestamp()
    ),
    vault_admin_key: str = "vault_admin",
    old_governance_token: str = "8a1cfae21368b8bebbbed9800fec304e95cce39a2a57dc35e2e3ebaa.4d494c4b",
    new_governance_token: str = "afbe91c0b44b3040e360057bf8354ead8c49c4979ae6ab7c4fbdc9eb.4d494c4b7632",
):
    build_compressed("spending", simple_pool.__file__)
    for script in (
        pool_nft,
        lp_token,
    ):
        build_compressed("minting", script.__file__)
    vault_contract_address = to_address(
        pycardano.Address.from_primitive(vault_contract_address)
    )
    latest_existing_mint_time = latest_vault_ft_mint_posix_time * 1000
    vault_admin = get_address(vault_admin_key).payment_part.payload
    old_governance_token = token_from_token_string(old_governance_token)
    new_governance_token = token_from_token_string(new_governance_token)
    build_compressed(
        "minting",
        vault_ft.__file__,
        args=[
            vault_contract_address.to_cbor().hex(),
            FinitePOSIXTime(latest_existing_mint_time).to_cbor().hex(),
            plutus_cbor_dumps(vault_admin).hex(),
            old_governance_token.to_cbor().hex(),
            new_governance_token.to_cbor().hex(),
        ],
    )

    for script, purpose in (
        (treasurer, "spending"),
        (value_store, "spending"),
        (licenses, "minting"),
        (gov_state, "spending"),
        (vote_permission_nft, "minting"),
        (tally, "spending"),
        (free_mint, "minting"),
    ):
        build_compressed(purpose, script.__file__)

    for script, purpose, unique_id in (
        (treasurer_nft, "minting", b"treasurer"),
        (gov_state_nft, "minting", b"gov_state"),
    ):
        build_compressed(
            purpose,
            script.__file__,
            args=[plutus_cbor_dumps(PlutusByteString(unique_id)).hex()],
        )

    _, gov_state_nft_script_hash, _ = get_contract(
        module_name(gov_state_nft), compressed=True
    )
    build_compressed(
        "minting",
        tally_auth_nft.__file__,
        args=[
            plutus_cbor_dumps(PlutusByteString(gov_state_nft_script_hash.payload)).hex()
        ],
    )

    _, _, tally_address = get_contract(module_name(tally), compressed=True)
    build_compressed(
        "minting",
        staking_vote_nft.__file__,
        args=[to_address(tally_address).to_cbor().hex()],
    )

    _, vote_permission_nft_script_hash, _ = get_contract(
        module_name(vote_permission_nft), compressed=True
    )
    build_compressed(
        "spending",
        staking.__file__,
        args=[
            plutus_cbor_dumps(
                PlutusByteString(vote_permission_nft_script_hash.payload)
            ).hex()
        ],
    )


if __name__ == "__main__":
    fire.Fire(main)
