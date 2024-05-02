from typing import Optional

import pycardano

from muesliswap_onchain_governance.api.db_models import sqlite_db
from opshin.prelude import Token


def parse_merged_tally_votes(
    weights: str, indices: str, proposals: str, proposal_indices: str
):
    weights = weights.split(";")
    indices = indices.split(";")
    proposals = proposals.split(";")
    proposal_indices = proposal_indices.split(";")
    votes = [{} for _ in range(len(weights))]
    for weight, index in zip(weights, indices):
        votes[int(index)]["weight"] = int(weight)
    for proposal, proposal_index in zip(proposals, proposal_indices):
        votes[int(proposal_index)]["proposal"] = pycardano.RawPlutusData.from_cbor(
            proposal
        ).to_dict()
    return votes


def query_tallies(closed: bool = True, open: bool = True):
    """
    Query tallies from the database.
    :param closed: Show closed tallies.
    :param open: Show open tallies.
    :return:
    """
    if open and closed:
        dateconstraint = ""
    elif open:
        dateconstraint = (
            "and (tp.end_time is NULL or DATETIME(tp.end_time) > DATETIME('now'))"
        )
    elif closed:
        dateconstraint = "and DATETIME(tp.end_time) <= DATETIME('now')"
    else:
        return []
    cursor = sqlite_db.execute_sql(
        """
        with merged_tally_votes as (
          select
          sum(tw.weight) as total_weight,
          group_concat(tw.weight, ';') as weights,
          group_concat(tw."index", ';') as indices,
          tw.tally_state_id
          from tallyweights tw
          group by tw.tally_state_id
        ),
        merged_tally_proposals as (
            select
            tp.tally_params_id,
            group_concat(hex(d.data), ';') as proposals,
            group_concat(tp."index", ';') as indices
            from tallyproposals tp
            join datum d on tp.proposal_id = d.id
            group by tp.tally_params_id
        )
        
        SELECT 
        tp.quorum,
        tp.end_time,
        tp.proposal_id,
        tally_auth_nft.policy_id,
        tally_auth_nft.asset_name,
        tp.staking_vote_nft_policy,
        staking_address.address_raw,
        gov_token.policy_id,
        gov_token.asset_name,
        tp.vault_ft_policy,
        mtv.total_weight,
        mtv.weights,
        mtv.indices,
        mtp.proposals,
        mtp.indices,
        tx_out.transaction_hash,
        tx_out.output_index
        FROM tallystate ts
        join tallyparams tp on ts.tally_params_id = tp.id
        join merged_tally_votes mtv on ts.id = mtv.tally_state_id
        join merged_tally_proposals mtp on tp.id = mtp.tally_params_id
        join transactionoutput tx_out on ts.transaction_output_id = tx_out.id
        join token tally_auth_nft on tp.tally_auth_nft_id = tally_auth_nft.id
        join address staking_address on tp.staking_address_id = staking_address.id
        join token gov_token on tp.governance_token_id = gov_token.id
        where tx_out.spent_in_block_id is NULL
        """
        + dateconstraint
        + """
        order by tp.end_time asc nulls first 
        """
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "quorum": row[0],
                "end_time": row[1],
                "proposal_id": row[2],
                "tally_auth_nft": {
                    "policy_id": row[3],
                    "asset_name": row[4],
                },
                "staking_vote_nft_policy_id": row[5],
                "staking_address": row[6],
                "gov_token": {
                    "policy_id": row[7],
                    "asset_name": row[8],
                },
                "vault_ft_policy_id": row[9],
                "total_weight": row[10],
                "votes": parse_merged_tally_votes(row[11], row[12], row[13], row[14]),
                "transaction_output": {
                    "transaction_hash": row[15],
                    "output_index": row[16],
                },
            }
        )
    return results


def query_tally_details_by_auth_nft_proposal_id(auth_nft: str, proposal_id: int):
    cursor = sqlite_db.execute_sql(
        """
    with merged_tally_votes as (
        select
        sum(tw.weight) as total_weight,
        group_concat(tw.weight, ';') as weights,
        group_concat(tw."index", ';') as indices,
        tw.tally_state_id
        from tallyweights tw
        group by tw.tally_state_id
    ),
    merged_tally_proposals as (
        select
        tp.tally_params_id,
        group_concat(hex(d.data), ';') as proposals,
        group_concat(tp."index", ';') as indices
        from tallyproposals tp
        join datum d on tp.proposal_id = d.id
        group by tp.tally_params_id
    ),
    merged_tally_creation_participants as (
        select
        tc.next_tally_state_id,
        group_concat(address.address_raw, ';') as addresses
        from tallycreation tc
        join tallycreationparticipants tcp on tc.id = tcp.tally_creation_id
        join address on tcp.address_id = address.id
        group by tc.next_tally_state_id
    )
    

    SELECT
    tp.quorum,
    tp.end_time,
    tp.proposal_id,
    tally_auth_nft.policy_id,
    tally_auth_nft.asset_name,
    tp.staking_vote_nft_policy,
    staking_address.address_raw,
    gov_token.policy_id,
    gov_token.asset_name,
    tp.vault_ft_policy,
    mtv.total_weight,
    mtv.weights,
    mtv.indices,
    mtp.proposals,
    mtp.indices,
    tcblk.slot,
    mtcps.addresses,
    tx_out.transaction_hash,
    tx_out.output_index
    FROM tallystate ts
    join tallyparams tp on ts.tally_params_id = tp.id
    join merged_tally_votes mtv on ts.id = mtv.tally_state_id
    join merged_tally_proposals mtp on tp.id = mtp.tally_params_id
    join transactionoutput tx_out on ts.transaction_output_id = tx_out.id
    join token tally_auth_nft on tp.tally_auth_nft_id = tally_auth_nft.id
    join address staking_address on tp.staking_address_id = staking_address.id
    join token gov_token on tp.governance_token_id = gov_token.id
    join tallystate tcts on tcts.tally_params_id = tp.id
    join tallycreation tc on tc.next_tally_state_id = tcts.id
    join "transaction" tctx on tc.transaction_id = tctx.id
    join "block" tcblk on tcblk.id = tctx.block_id
    join merged_tally_creation_participants mtcps on tc.next_tally_state_id = mtcps.next_tally_state_id
    where tx_out.spent_in_block_id is NULL
    and tally_auth_nft.policy_id = ?
    and tally_auth_nft.asset_name = ?
    and tp.proposal_id = ?
    """,
        (*auth_nft.split("."), proposal_id),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "quorum": row[0],
                "end_time": row[1],
                "proposal_id": row[2],
                "tally_auth_nft": {
                    "policy_id": row[3],
                    "asset_name": row[4],
                },
                "staking_vote_nft_policy_id": row[5],
                "staking_address": row[6],
                "gov_token": {
                    "policy_id": row[7],
                    "asset_name": row[8],
                },
                "vault_ft_policy_id": row[9],
                "total_weight": row[10],
                "votes": parse_merged_tally_votes(row[11], row[12], row[13], row[14]),
                "creation_slot": row[15],
                "creators": row[16].split(";"),
                "transaction_output": {
                    "transaction_hash": row[17],
                    "output_index": row[18],
                },
            }
        )
    return results


def query_tally_auth_nft_proposal_id(transaction_hash: str, transaction_index: int):
    """
    Obtain the auth nft and proposal id for a tally that once had a given transaction output
    :param transaction_hash:
    :param transaction_index:
    :return: (auth_nft, proposal_id) or None if the transaction output is not part of a tally
    """
    cursor = sqlite_db.execute_sql(
        """
    SELECT
    tk.policy_id,
    tk.asset_name,
    tp.proposal_id
    FROM tallystate ts
    join tallyparams tp on ts.tally_params_id = tp.id
    join transactionoutput tx_out on ts.transaction_output_id = tx_out.id
    join token tk on tp.tally_auth_nft_id = tk.id
    where tx_out.transaction_hash = ?
    and tx_out.output_index = ?
    """,
        (transaction_hash, transaction_index),
    )
    for row in cursor.fetchall():
        return (Token(bytes.fromhex(row[0]), bytes.fromhex(row[1])), row[2])
    return None


def query_tally_details_by_tx_out(transaction_hash: str, transaction_index: int):
    """
    Returns the latest tally details for a tally that has at some point had a transaction output with the given hash and index.
    :param transaction_hash:
    :param transaction_index:
    :return:
    """
    auth_nft_proposal_id = query_tally_auth_nft_proposal_id(
        transaction_hash, transaction_index
    )
    if auth_nft_proposal_id is None:
        return []
    return query_tally_details_by_auth_nft_proposal_id(*auth_nft_proposal_id)


def query_tally_details_by_auth_nft_proposal_id_with_user_vote(
    auth_nft: str, proposal_id: int, user_address: str
):
    cursor = sqlite_db.execute_sql(
        """
    with merged_tally_votes as (
        select
        sum(tw.weight) as total_weight,
        group_concat(tw.weight, ';') as weights,
        group_concat(tw."index", ';') as indices,
        tw.tally_state_id
        from tallyweights tw
        group by tw.tally_state_id
    ),
    merged_tally_proposals as (
        select
        tp.tally_params_id,
        group_concat(hex(d.data), ';') as proposals,
        group_concat(tp."index", ';') as indices
        from tallyproposals tp
        join datum d on tp.proposal_id = d.id
        group by tp.tally_params_id
    ),
    merged_tally_creation_participants as (
        select
        tc.next_tally_state_id,
        group_concat(address.address_raw, ';') as addresses
        from tallycreation tc
        join tallycreationparticipants tcp on tc.id = tcp.tally_creation_id
        join address on tcp.address_id = address.id
        group by tc.next_tally_state_id
    ),
    user_staking_participation as (
        select
        sp.tally_auth_nft_id,
        sp.proposal_id,
        sp.weight,
        sp.proposal_index,
        staking_blk.slot
        from stakingparticipation sp
        join stakingparticipationinstaking spis on sp.id = spis.participation_id
        join stakingstate ss on spis.staking_state_id = ss.id
        join stakingparams sparams on ss.staking_params_id = sparams.id
        join address sa on sa.id = sparams.owner_id
        join transactionoutput staking_tx_out on ss.transaction_output_id = staking_tx_out.id
        join "transaction" staking_tx on staking_tx.id = staking_tx_out.transaction_id
        join "block" staking_blk on staking_blk.id = staking_tx.block_id
        where sa.address_raw = ?
    )


    SELECT
    tp.quorum,
    tp.end_time,
    tp.proposal_id,
    tally_auth_nft.policy_id,
    tally_auth_nft.asset_name,
    tp.staking_vote_nft_policy,
    staking_address.address_raw,
    gov_token.policy_id,
    gov_token.asset_name,
    tp.vault_ft_policy,
    mtv.total_weight,
    mtv.weights,
    mtv.indices,
    mtp.proposals,
    mtp.indices,
    tcblk.slot,
    mtcps.addresses,
    tx_out.transaction_hash,
    tx_out.output_index,
    spart.weight,
    spart.proposal_index
    -- get the tally details
    FROM tallystate ts
    join tallyparams tp on ts.tally_params_id = tp.id
    join merged_tally_votes mtv on ts.id = mtv.tally_state_id
    join merged_tally_proposals mtp on tp.id = mtp.tally_params_id
    join transactionoutput tx_out on ts.transaction_output_id = tx_out.id
    join token tally_auth_nft on tp.tally_auth_nft_id = tally_auth_nft.id
    join address staking_address on tp.staking_address_id = staking_address.id
    join token gov_token on tp.governance_token_id = gov_token.id
    join tallystate tcts on tcts.tally_params_id = tp.id
    join tallycreation tc on tc.next_tally_state_id = tcts.id
    join "transaction" tctx on tc.transaction_id = tctx.id
    join "block" tcblk on tcblk.id = tctx.block_id
    join merged_tally_creation_participants mtcps on tc.next_tally_state_id = mtcps.next_tally_state_id
    left outer join user_staking_participation spart on tp.tally_auth_nft_id = spart.tally_auth_nft_id and tp.proposal_id = spart.proposal_id
    -- get last vote on this tally
    join tallyvote tv on tv.next_tally_state_id = ts.id
    join "transaction" last_vote_tx on tv.transaction_id = last_vote_tx.id
    join "block" last_vote_blk on last_vote_blk.id = last_vote_tx.block_id
    where tx_out.spent_in_block_id is NULL
    and tally_auth_nft.policy_id = ?
    and tally_auth_nft.asset_name = ?
    and tp.proposal_id = ?
    and spart.slot <= last_vote_blk.slot
    order by spart.slot desc
    limit 1
    """,
        (
            user_address,
            *auth_nft.split("."),
            proposal_id,
        ),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "quorum": row[0],
                "end_time": row[1],
                "proposal_id": row[2],
                "tally_auth_nft": {
                    "policy_id": row[3],
                    "asset_name": row[4],
                },
                "staking_vote_nft_policy_id": row[5],
                "staking_address": row[6],
                "gov_token": {
                    "policy_id": row[7],
                    "asset_name": row[8],
                },
                "vault_ft_policy_id": row[9],
                "total_weight": row[10],
                "votes": parse_merged_tally_votes(row[11], row[12], row[13], row[14]),
                "creation_slot": row[15],
                "creators": row[16].split(";"),
                "transaction_output": {
                    "transaction_hash": row[17],
                    "output_index": row[18],
                },
                "user_vote": {"weight": row[19], "proposal_index": row[20]},
            }
        )
    return results


def query_tally_details_by_tx_out_with_user_vote(
    transaction_hash: str, transaction_index: int, user_address: str
):
    """
    Returns the latest tally details for a tally that has at some point had a transaction output with the given hash and index.
    :param transaction_hash:
    :param transaction_index:
    :return:
    """
    auth_nft_proposal_id = query_tally_auth_nft_proposal_id(
        transaction_hash, transaction_index
    )
    if auth_nft_proposal_id is None:
        return []
    return query_tally_details_by_auth_nft_proposal_id_with_user_vote(
        *auth_nft_proposal_id, user_address
    )


def query_all_user_votes_for_tally(auth_nft: str, proposal_id: int):
    last_vote_slot, tally_state_id = sqlite_db.execute_sql(
        """
    SELECT
    last_vote_blk.slot,
    ts.id
    -- get the tally details
    FROM tallystate ts
    join tallyparams tp on ts.tally_params_id = tp.id
    join transactionoutput tx_out on ts.transaction_output_id = tx_out.id
    join token tally_auth_nft on tp.tally_auth_nft_id = tally_auth_nft.id
    join tallystate tcts on tcts.tally_params_id = tp.id
    -- get last vote on this tally
    join tallyvote tv on tv.next_tally_state_id = ts.id
    join "transaction" last_vote_tx on tv.transaction_id = last_vote_tx.id
    join "block" last_vote_blk on last_vote_blk.id = last_vote_tx.block_id
    where tx_out.spent_in_block_id is NULL
    and tally_auth_nft.policy_id = ?
    and tally_auth_nft.asset_name = ?
    and tp.proposal_id = ?
    """,
        (
            *auth_nft.split("."),
            proposal_id,
        ),
    ).fetchall()[0]
    cursor = sqlite_db.execute_sql(
        """
    with latest_staking_state_before_vote_per_user as (
        select
        max(blk.slot) as slot,
        sp.owner_id
        from stakingstate ss
        join stakingparams sp on ss.staking_params_id = sp.id
        join transactionoutput tx_out on ss.transaction_output_id = tx_out.id
        join "transaction" tx on tx_out.transaction_id = tx.id
        join "block" blk on tx.block_id = blk.id
        where blk.slot <= ?
        group by sp.owner_id
    )


    SELECT
    sa.address_raw,
    sp.proposal_index,
    sp.weight
    FROM tallystate ts
    join tallyparams tp on ts.tally_params_id = tp.id
    join stakingparticipation sp on sp.tally_auth_nft_id = tp.tally_auth_nft_id and sp.proposal_id = tp.proposal_id
    join stakingparticipationinstaking spis on sp.id = spis.participation_id
    join stakingstate ss on spis.staking_state_id = ss.id
    join stakingparams sparams on ss.staking_params_id = sparams.id
    join address sa on sa.id = sparams.owner_id
    join transactionoutput tx_out on ss.transaction_output_id = tx_out.id
    join "transaction" tx on tx_out.transaction_id = tx.id
    join "block" blk on tx.block_id = blk.id
    join latest_staking_state_before_vote_per_user ls on ls.owner_id = sa.id
    where ts.id = ?
    and blk.slot = ls.slot
    """,
        (
            last_vote_slot,
            tally_state_id,
        ),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {
                "address": row[0],
                "proposal_index": row[1],
                "weight": row[2],
            }
        )
    return results


if __name__ == "__main__":
    print(query_tallies(True, False))
    print(query_tallies(False, True))
    print(query_tallies(True, True))
    print(query_tallies(False, False))
    print(
        query_tally_details_by_auth_nft_proposal_id(
            "471b0b6f3fab69f9c6e8c1c1389782a410a8689d97e22a22ac24b30f.bc0a47f8459162152c33913f9d4e50d2340459ce4b6197761967d64368e0e50c",
            3,
        )
    )
    print(
        query_tally_details_by_tx_out(
            "03b0238d4418cba3dde0f6d2f92495f16ee641fd154d1b93bdb4155a7afdd93d", 0
        )
    )
    print(
        query_tally_details_by_auth_nft_proposal_id_with_user_vote(
            "471b0b6f3fab69f9c6e8c1c1389782a410a8689d97e22a22ac24b30f.bc0a47f8459162152c33913f9d4e50d2340459ce4b6197761967d64368e0e50c",
            1,
            "607195078bd15707f7a74581a317c41c14be16ffe7ce7dc0f22b039713",
        )
    )
    print(
        query_all_user_votes_for_tally(
            "471b0b6f3fab69f9c6e8c1c1389782a410a8689d97e22a22ac24b30f.bc0a47f8459162152c33913f9d4e50d2340459ce4b6197761967d64368e0e50c",
            2,
        )
    )
