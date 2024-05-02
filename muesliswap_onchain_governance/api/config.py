import pycardano
from pycardano import Network

from ..utils.contracts import module_name
from ..utils import network, contracts

from ..onchain.gov_state import gov_state_nft
from ..onchain.staking import vote_permission_nft
from ..onchain.licenses import licenses
from ..onchain.treasury import treasurer_nft

# Only these scripts need to be hardcoded
# And should also change seldomly
_, gov_state_nft_policy_id, _ = contracts.get_contract(
    module_name(gov_state_nft), compressed=True
)
_, vote_permission_nft_policy_id, _ = contracts.get_contract(
    module_name(vote_permission_nft), compressed=True
)
_, licenses_policy_id, _ = contracts.get_contract(
    module_name(licenses), compressed=True
)
_, treasurer_nft_policy_id, _ = contracts.get_contract(
    module_name(treasurer_nft), compressed=True
)

# default: start from a block around 19 feb 2024
start_block_slot = 52616248 if network == Network.TESTNET else 72316796
start_block_hash = (
    "94b3e8daeec3babc929a1180854687b29ba797cd0173509ff1e90d41a6e7fb59"
    if network == Network.TESTNET
    else "c58a24ba8203e7629422a24d9dc68ce2ed495420bf40d9dab124373655161a20"
)
