MuesliSwap On-Chain Governance
------------------------------

This repository contains the documentation and code for the implementation
of the MuesliSwap On-Chain Governance funded in Fund 10 by Project Catalyst [1].

### Structure

The directory `report` contains a detailed report on the outline and planned implementation and integration
of the On-Chain Governance system into the MuesliSwap governance platform.
It further outlines a short comparison to alternative implementations.

The directory `muesliswap_onchain_governance` contains the code for the blockchain part of the On-Chain Governance system.
The following subdirectories are present:

- `onchain`: Contains the code for the on-chain part of the governance system i.e. Smart Contracts written in OpShin
- `offchain`: Contains the code for the off-chain part of the governance system i.e. building and submitting transactions for interaction with the Smart Contracts
- `api`: Contains code for the REST API that provides information about the governance system
    - `chain_querier`: Contains the code for querying the blockchain for information about the governance system and tracking the current state of the system in a database
    - `db_querier`: Contains the code for querying data from the database to prepare it for the REST API
    - `server`: Contains the code for the server that supplies information about the governance system via a REST API

### Operating the DAO

The DAO can be initialized by deploying the smart contracts in the `onchain` directory using the scripts provided in the `offchain` directory.
For this, you need to have an Ogmios endpoint available and set the environment variables `OGMIOS_API_HOST`, `OGMIOS_API_PROTOCOL` and `OGMIOS_API_PORT` to the respective values (default `localhost`, `ws` and `1337`).
Further, install the current project.

```bash
poetry install
```

Create and fund two wallets for the DAO administration and for voting.
You can use the [testnet faucet](https://docs.cardano.org/cardano-testnet/tools/faucet/) to fund them, make sure to select `preprod` network!.

```bash
python3 -m muesliswap_onchain_governance.create_key_pair creator
python3 -m muesliswap_onchain_governance.create_key_pair voter
python3 -m muesliswap_onchain_governance.create_key_pair vault_admin
```

Then, build the smart contracts. Note that this requires the [`aiken`](https://aiken-lang.org) executable present in the `PATH` environment variable. The original contract was built with version `aiken v1.0.26-alpha+075668b`.

```bash
python3 -m muesliswap_onchain_governance.build
``` 

Create a governance thread using the `creator` wallet.

```bash
python3 -m muesliswap_onchain_governance.offchain.gov_state.init --wallet creator --governance_token bd976e131cfc3956b806967b06530e48c20ed5498b46a5eb836b61c2.744d494c4b
```

This will create a new governance thread and print the thread id. You can use this thread id to interact with the governance system.
For convenience, you can update the `GOV_STATE_NFT_TK_NAME` in `muesliswap_onchain_governance/offchain/util.py` to the thread id.
Next, you can create a tally using the `creator` wallet.

```bash
python3 -m muesliswap_onchain_governance.offchain.gov_state.create_tally --wallet creator
```

The default for this tally is to open for 10 minutes and allow choosing between a treasury payout to `voter` and a license mint.
> Note: in a production environment you would never want a tally with expiry date for licenses, as this would allow for a license to be minted indefinitely.
Next, you can register the `voter` wallet as a voter by locking the governance tokens in the staking contract and using the stake to vote.

```bash
python3 -m muesliswap_onchain_governance.offchain.staking.init --wallet voter
python3 -m muesliswap_onchain_governance.offchain.tally.add_vote_tally --wallet voter --proposal_id 1 --proposal_index 1
```

This will lock the governance tokens in the staking contract and use the stake to vote for the second (index 1) proposal in the first tally.
This proposal empowers the DAO to a treasury payout to the `voter` wallet.
After the proposal ended (i.e. default 10 minutes), you can execute the tally using any wallet.
For this you need to first initialize the treasury (again for convenience update the `TREASURER_STATE_NFT_TK_NAME`), deposit funds and then execute the tally.

```bash
python3 -m muesliswap_onchain_governance.offchain.treasury.init --wallet creator
python3 -m muesliswap_onchain_governance.offchain.treasury.deposit --wallet creator
python3 -m muesliswap_onchain_governance.offchain.treasury.payout --wallet voter
```

### Upgrading a liquidity pool

The DAO can also be used to upgrade a liquidity pool. For this, you need to create a new liquidity pool and a proposal to upgrade the liquidity pool.
The following commands will create a new liquidity pool and a proposal to upgrade the liquidity pool.

```bash
python3 -m muesliswap_onchain_governance.offchain.simple_pool.init --wallet creator
python3 -m muesliswap_onchain_governance.offchain.gov_state.create_tally --wallet creator
python3 -m muesliswap_onchain_governance.offchain.tally.add_vote_tally --wallet voter --proposal_index 3
python3 -m muesliswap_onchain_governance.offchain.simple_pool.upgrade --wallet voter
```

[1]: [DAO Treasury & Protocol Parameter Management via On-Chain Governance - By MuesliSwap](https://projectcatalyst.io/funds/10/f10-daos-less3-cardano/dao-treasury-and-protocol-parameter-management-via-on-chain-governance-by-muesliswap)