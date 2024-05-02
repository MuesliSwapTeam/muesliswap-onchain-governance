import cbor2

from muesliswap_onchain_governance.onchain.util import Participation
from opshin.ledger.api_v2 import FinitePOSIXTime
from .util import parse_merged_assets
from ..db_models import sqlite_db


def parse_merged_participations(
    end_times: str,
    weights: str,
    proposal_indices: str,
    proposal_ids: str,
    tally_transaction_hashes: str,
    tally_output_indices: str,
):
    """
    Parse the merged participations
    :param end_times: The end times
    :param weights: The weights
    :param proposal_indices: The proposal indices
    :param tally_transaction_hashes: The tally transaction hashes
    :param tally_output_indices: The tally output indices
    :return: A list of participations
    """
    end_times = end_times.split(";") if end_times else []
    weights = weights.split(";") if weights else []
    proposal_indices = proposal_indices.split(";") if proposal_indices else []
    proposal_ids = proposal_ids.split(";") if proposal_ids else []
    tally_transaction_hashes = (
        tally_transaction_hashes.split(";") if tally_transaction_hashes else []
    )
    tally_output_indices = (
        tally_output_indices.split(";") if tally_output_indices else []
    )
    participations = [
        {
            "end_time": end_time,
            "weight": weight,
            "proposal_index": proposal_index,
            "proposal_id": proposal_id,
            "tally": {
                "transaction_hash": tally_transaction_hash,
                "output_index": tally_output_index,
            },
        }
        for end_time, weight, proposal_index, proposal_id, tally_transaction_hash, tally_output_index in zip(
            end_times,
            weights,
            proposal_indices,
            proposal_ids,
            tally_transaction_hashes,
            tally_output_indices,
        )
    ]
    return participations


def parse_delegated_actions(
    delegated_actions: str,
):
    """
    Parse the delegated actions
    :param delegated_actions: The delegated actions
    :return: A list of delegated actions
    """
    delegated_actions = (
        [x for x in delegated_actions.split(";") if x] if delegated_actions else []
    )
    parsed_actions = []
    for delegated_action in delegated_actions:
        parsed = cbor2.loads(bytes.fromhex(delegated_action)).value[1]
        if not isinstance(parsed, cbor2.CBORTag):
            continue
        tag = "add_vote" if parsed.tag == 122 else "retract_vote"
        try:
            participation = Participation.from_primitive(parsed.value[0])
        except Exception:
            continue
        parsed_actions.append(
            {
                "tag": tag,
                "participation": {
                    "end_time": str(participation.end_time.time)
                    if isinstance(participation.end_time, FinitePOSIXTime)
                    else None,
                    "weight": str(participation.weight),
                    "proposal_index": participation.proposal_index,
                    "proposal_id": participation.proposal_id,
                    "tally_auth_nft": {
                        "policy_id": participation.tally_auth_nft.policy_id.hex(),
                        "asset_name": participation.tally_auth_nft.token_name.hex(),
                    },
                },
            }
        )

    return parsed_actions


def query_staking_positions_per_wallet(
    wallet: str,
):
    """
    Query the staking positions per wallet
    :param wallet: Hex encoded wallet address
    :return:
    """
    cursor = sqlite_db.execute_sql(
        """
        with merged_transaction_output_value as (
            select
            group_concat(tk.policy_id, ';') as policy_ids,
            group_concat(tk.asset_name, ';') as asset_names,
            group_concat(tov.amount, ';') as amounts,
            group_concat(hex(d.data), ';') as delegated_actions,
            tov.transaction_output_id
            from transactionoutputvalue tov
            join token tk on tov.token_id = tk.id
            left outer join votepermission vp on tov.token_id = vp.token_id
            left outer join datum d on vp.delegated_action_id = d.id
            group by tov.transaction_output_id
        )
        
        SELECT
        owner_a.address_raw,
        txo.transaction_hash,
        txo.output_index,
        tov.policy_ids,
        tov.asset_names,
        tov.amounts,
        group_concat(spt.end_time, ';'),
        group_concat(spt.weight, ';'),
        group_concat(spt.proposal_index, ';'),
        group_concat(spt.proposal_id, ';'),
        group_concat(tally_txo.transaction_hash, ';'),
        group_concat(tally_txo.output_index, ';'),
        sp.vault_ft_policy,
        gov_tk.policy_id,
        gov_tk.asset_name,
        tov.delegated_actions,
        tally_auth_tk.policy_id,
        tally_auth_tk.asset_name
        FROM stakingstate ss
        JOIN stakingparams sp on ss.staking_params_id = sp.id
        JOIN address owner_a on sp.owner_id = owner_a.id
        JOIN transactionoutput txo on ss.transaction_output_id = txo.id
        JOIN merged_transaction_output_value tov on tov.transaction_output_id = txo.id
        JOIN token gov_tk on sp.governance_token_id = gov_tk.id
        JOIN token tally_auth_tk on sp.tally_auth_nft_id = tally_auth_tk.id
        left outer JOIN stakingparticipationinstaking spis on ss.id = spis.staking_state_id
        left outer JOIN stakingparticipation spt on spis.participation_id = spt.id
        left outer join tallyparams tp on (spt.tally_auth_nft_id = tp.tally_auth_nft_id and spt.proposal_id = tp.proposal_id)
        left outer join tallystate ts on tp.id = ts.tally_params_id
        left outer join transactionoutput tally_txo on ts.transaction_output_id = tally_txo.id
        WHERE owner_a.address_raw = ? -- only for the given wallet
        and txo.spent_in_block_id is null -- only unspent outputs
        and tally_txo.spent_in_block_id is null -- only unspent tally outputs
        group by owner_a.address_raw, txo.transaction_hash, txo.output_index, tov.policy_ids, tov.asset_names, tov.amounts, sp.vault_ft_policy, gov_tk.policy_id, gov_tk.asset_name
        """,
        (wallet,),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "owner": row[0],
                "transaction_hash": row[1],
                "output_index": row[2],
                "funds": parse_merged_assets(row[3], row[4], row[5]),
                "participations": parse_merged_participations(
                    row[6], row[7], row[8], row[9], row[10], row[11]
                ),
                "vault_ft_policy": row[12],
                "gov_token": {"policy_id": row[13], "asset_name": row[14]},
                "delegated_actions": parse_delegated_actions(row[15]),
                "tally_auth_nft": {"policy_id": row[16], "asset_name": row[17]},
            }
        )
    return results


def query_staking_history_per_wallet(wallet: str):
    """
    Query the staking history per wallet
    :param wallet: Hex encoded wallet address
    :return:
    """
    cursor = sqlite_db.execute_sql(
        """
        with merged_staking_deposit_delta as (
            select
            group_concat(tk.policy_id, ';') as policy_ids,
            group_concat(tk.asset_name, ';') as asset_names,
            group_concat(sdd.amount, ';') as amounts,
            group_concat(hex(d.data), ';') as delegated_actions,
            sdd.staking_deposit_id
            from stakingdepositdelta sdd
            join token tk on sdd.token_id = tk.id
            left outer join votepermission vp on sdd.token_id = vp.token_id
            left outer join datum d on vp.delegated_action_id = d.id
            group by sdd.staking_deposit_id
        ),
        merged_participation_additions as (
            select
            group_concat(spt.end_time, ';') as end_times,
            group_concat(spt.weight, ';') as weights,
            group_concat(spt.proposal_index, ';') as proposal_indices,
            group_concat(spt.proposal_id, ';') as proposal_ids,
            group_concat(tally_txo.transaction_hash, ';') as tally_transaction_hashes,
            group_concat(tally_txo.output_index, ';') as tally_output_indices,
            spa.staking_deposit_id
            from stakingdepositparticipationadded spa
            join stakingparticipationinstaking spis on spa.staking_deposit_id = spis.staking_state_id
            join stakingparticipation spt on spis.participation_id = spt.id
            left outer join tallyparams tp on (spt.tally_auth_nft_id = tp.tally_auth_nft_id and spt.proposal_id = tp.proposal_id)
            left outer join tallystate ts on tp.id = ts.tally_params_id
            left outer join transactionoutput tally_txo on ts.transaction_output_id = tally_txo.id
            where tally_txo.spent_in_block_id is null
            group by spa.staking_deposit_id
        ),
        merged_participation_retractions as (
            select
            group_concat(spt.end_time, ';') as end_times,
            group_concat(spt.weight, ';') as weights,
            group_concat(spt.proposal_index, ';') as proposal_indices,
            group_concat(spt.proposal_id, ';') as proposal_ids,
            group_concat(tally_txo.transaction_hash, ';') as tally_transaction_hashes,
            group_concat(tally_txo.output_index, ';') as tally_output_indices,
            spa.staking_deposit_id
            from stakingdepositparticipationremoved spa
            join stakingparticipationinstaking spis on spa.staking_deposit_id = spis.staking_state_id
            join stakingparticipation spt on spis.participation_id = spt.id
            left outer join tallyparams tp on (spt.tally_auth_nft_id = tp.tally_auth_nft_id and spt.proposal_id = tp.proposal_id)
            left outer join tallystate ts on tp.id = ts.tally_params_id
            left outer join transactionoutput tally_txo on ts.transaction_output_id = tally_txo.id
            where tally_txo.spent_in_block_id is null
            -- todo: join with block and mark as retraction only if the block is before the end time of the participation
            group by spa.staking_deposit_id
        )
        
        SELECT
        b.slot,
        tx.transaction_hash,
        tx.block_index,
        sdd.policy_ids,
        sdd.asset_names,
        sdd.amounts,
        sdd.delegated_actions,
        spa.end_times,
        spa.weights,
        spa.proposal_indices,
        spa.proposal_ids,
        spa.tally_transaction_hashes,
        spa.tally_output_indices,
        spr.end_times,
        spr.weights,
        spr.proposal_indices,
        spr.proposal_ids,
        spr.tally_transaction_hashes,
        spr.tally_output_indices,
        owner_a.address_raw
        from stakingdeposit sd
        join "transaction" tx on sd.transaction_id = tx.id
        join main.block b on tx.block_id = b.id
        join stakingstate ss on sd.next_staking_state_id = ss.id
        join stakingparams sps on sps.id = ss.staking_params_id
        join address owner_a on sps.owner_id = owner_a.id
        left outer join merged_staking_deposit_delta sdd on sdd.staking_deposit_id = sd.id
        left outer join merged_participation_additions spa on spa.staking_deposit_id = sd.id
        left outer join merged_participation_retractions spr on spr.staking_deposit_id = sd.id
        where owner_a.address_raw = ?
        order by b.slot, tx.block_index, tx.transaction_hash
        """,
        (wallet,),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "slot": row[0],
                "transaction_hash": row[1],
                "block_index": row[2],
                "funds": parse_merged_assets(row[3], row[4], row[5]),
                "delegated_actions": parse_delegated_actions(row[6]),
                "participations_added": parse_merged_participations(
                    row[7], row[8], row[9], row[10], row[11], row[12]
                ),
                "participations_retracted": parse_merged_participations(
                    row[13], row[14], row[15], row[16], row[17], row[18]
                ),
                "owner": row[19],
            }
        )
    return results


if __name__ == "__main__":
    print(
        query_staking_positions_per_wallet(
            "607195078bd15707f7a74581a317c41c14be16ffe7ce7dc0f22b039713"
        )
    )
    print(
        query_staking_history_per_wallet(
            "607195078bd15707f7a74581a317c41c14be16ffe7ce7dc0f22b039713"
        )
    )
