from .util import parse_merged_assets
from ..db_models import sqlite_db


def query_treasury_history():
    """
    Query the treasury deposits and payouts
    :return: A list of treasury deposits and payouts in chronological order
    """
    cursor = sqlite_db.execute_sql(
        """
        with merged_treasury_delta_value as (
            select
            group_concat(tk.policy_id, ';') as policy_ids,
            group_concat(tk.asset_name, ';') as asset_names,
            group_concat(tdv.amount, ';') as amounts,
            tdv.treasury_delta_id
            from treasurydeltavalue tdv
            join token tk on tdv.token_id = tk.id
            group by tdv.treasury_delta_id
        ),
        merged_treasury_payout as (
            select
            tp.treasury_delta_id,
            payout_to.transaction_hash as payout_transaction_hash,
            payout_to.output_index as payout_output_index,
            tally_to.transaction_hash as tally_transaction_hash,
            tally_to.output_index as tally_output_index
            from treasurypayout tp
            join transactionoutput payout_to on tp.payout_output_id = payout_to.id
            join tallystate ts on tp.tally_state_id = ts.id
            join transactionoutput tally_to on ts.transaction_output_id = tally_to.id
        )
        
        SELECT 
        b.slot,
        tx.transaction_hash,
        tx.block_index,
        tp.payout_transaction_hash,
        tp.payout_output_index,
        tp.tally_transaction_hash,
        tp.tally_output_index,
        tdv.policy_ids,
        tdv.asset_names,
        tdv.amounts
        FROM "treasurydelta" td
        join "transaction" tx on td.transaction_id = tx.id
        join "block" b on tx.block_id = b.id
        left outer join merged_treasury_delta_value tdv on tdv.treasury_delta_id = td.id
        left outer join merged_treasury_payout tp on tp.treasury_delta_id = td.id
        ORDER BY b.slot, tx.block_index, tx.transaction_hash
        """
    )
    results = []
    for row in cursor.fetchall():
        assets = parse_merged_assets(row[7], row[8], row[9]) if row[9] else []
        action = {
            "slot": row[0],
            "transaction_hash": row[1],
            "block_index": row[2],
            "payout": {"transaction_hash": row[3], "output_index": row[4]}
            if row[3]
            else None,
            "tally_id": {"transaction_hash": row[5], "output_index": row[6]}
            if row[5]
            else None,
            "delta": assets,
            "action": "payout" if row[3] else ("deposit" if assets else "consolidate"),
        }
        results.append(action)
    return results


def query_historical_treasury_funds():
    cursor = sqlite_db.execute_sql(
        """
        select
        tdv_block.slot,
        tk.policy_id,
        tk.asset_name,
        sum(tov.amount) as amount
        from 
        treasurydelta tdv
        join "transaction" tdv_tx on tdv.transaction_id = tdv_tx.id
        join "block" tdv_block on tdv_tx.block_id = tdv_block.id,
        valuestorestate vss
        join transactionoutput txo on vss.transaction_output_id = txo.id
        join transactionoutputvalue tov on txo.id = tov.transaction_output_id
        join token tk on tov.token_id = tk.id
        join "transaction" created_tx on txo.transaction_id = created_tx.id
        join "block" created_blk on created_tx.block_id = created_blk.id
        left outer join "block" spent_blk on txo.spent_in_block_id = spent_blk.id
        where created_blk.slot <= tdv_block.slot
        and (txo.spent_in_block_id is null or spent_blk.slot > tdv_block.slot)
        group by tdv_block.slot, tk.policy_id, tk.asset_name
        """,
    )
    results = []
    current_slot = 0
    current_funds = []
    for row in cursor.fetchall():
        if row[0] != current_slot:
            results.append({"slot": current_slot, "funds": current_funds})
            current_slot = row[0]
            current_funds = []
        current_funds.append(
            {
                "policy_id": row[1],
                "asset_name": row[2],
                "amount": row[3],
            }
        )
    return results


def query_current_treasury_funds():
    cursor = sqlite_db.execute_sql(
        """
        select
        tk.policy_id,
        tk.asset_name,
        sum(tov.amount) as amount
        from valuestorestate vss
        join transactionoutput txo on vss.transaction_output_id = txo.id
        join transactionoutputvalue tov on txo.id = tov.transaction_output_id
        join token tk on tov.token_id = tk.id
        where txo.spent_in_block_id is null
        group by tk.policy_id, tk.asset_name
        """,
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "policy_id": row[0],
                "asset_name": row[1],
                "amount": row[2],
            }
        )
    return results


if __name__ == "__main__":
    print(query_treasury_history())
    print(query_historical_treasury_funds())
    print(query_current_treasury_funds())
