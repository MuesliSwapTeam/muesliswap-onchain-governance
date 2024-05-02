from muesliswap_onchain_governance.offchain.gov_state.init import main
from test.offchain.util import DEFAULT_TEST_CONFIG, wait_for_tx


def test_init_gov_state():
    creation_tx, gov_nft_name = main(
        wallet=DEFAULT_TEST_CONFIG.creator_wallet_name,
        governance_token=DEFAULT_TEST_CONFIG.governance_token,
        min_quorum=DEFAULT_TEST_CONFIG.min_quorum,
        min_proposal_duration=DEFAULT_TEST_CONFIG.min_proposal_duration,
        vault_ft_policy_id=DEFAULT_TEST_CONFIG.vault_ft_policy_id,
    )
    wait_for_tx(creation_tx)
