import os
import pytest
import vcr
import requests
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP, PUBLIC_NODE_URL, RewardsType
from tests.utils import Constants

# Block APIs
from src.tzkt.tzkt_block_api import TzKTBlockApiImpl
from src.blockwatch.tzpro_block_api import TzProBlockApiImpl
from src.rpc.rpc_block_api import RpcBlockApiImpl

# Reward APIs
from src.tzkt.tzkt_reward_api import TzKTRewardApiImpl
from src.blockwatch.tzpro_reward_api import TzProRewardApiImpl

MAINNET_ADDRESS_DELEGATOR = Constants.MAINNET_ADDRESS_DELEGATOR
MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
MAINNET_ADDRESS_BAKEXTZ4ME_BAKER = Constants.MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
GHOSTNET_ADDRESS_STAKENOW_BAKER = Constants.GHOSTNET_ADDRESS_STAKENOW_BAKER
MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT = Constants.MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT

TZPRO_API_KEY = os.environ.get("TZPRO_API_KEY")

# These tests should not be mocked but test the overall consistency
# accross all tezos APIs which are available in TRD


@pytest.fixture
def address_block_api_tzkt():
    return TzKTBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


@pytest.fixture
def address_block_api_tzpro():
    return TzProBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], TZPRO_API_KEY)


@pytest.fixture
def address_block_api_rpc():
    return RpcBlockApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], PUBLIC_NODE_URL["MAINNET"]
    )


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_revelation.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_revelation(
    address_block_api_tzkt, address_block_api_tzpro, address_block_api_rpc
):
    assert address_block_api_tzkt.get_revelation(
        MAINNET_ADDRESS_DELEGATOR
    ) == address_block_api_tzpro.get_revelation(MAINNET_ADDRESS_DELEGATOR)
    assert address_block_api_tzkt.get_revelation(
        MAINNET_ADDRESS_DELEGATOR
    ) == address_block_api_rpc.get_revelation(MAINNET_ADDRESS_DELEGATOR)
    assert address_block_api_tzpro.get_revelation(
        MAINNET_ADDRESS_DELEGATOR
    ) == address_block_api_rpc.get_revelation(MAINNET_ADDRESS_DELEGATOR)


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_current_cycle_and_level.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_current_cycle_and_level(
    address_block_api_tzkt, address_block_api_tzpro, address_block_api_rpc
):
    cycle_tzkt, level_tzkt = address_block_api_tzkt.get_current_cycle_and_level()
    (
        cycle_tzpro,
        level_tzpro,
    ) = address_block_api_tzpro.get_current_cycle_and_level()
    cycle_rpc, level_rpc = address_block_api_rpc.get_current_cycle_and_level()

    assert cycle_tzkt == cycle_tzpro
    assert cycle_rpc == cycle_tzpro
    assert cycle_tzkt == cycle_rpc

    # Allow a delta of 1 for level query
    assert abs(level_tzkt - level_tzpro) <= 1
    assert abs(level_rpc - level_tzpro) <= 1
    assert abs(level_tzkt - level_rpc) <= 1


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_delegatable.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_delegatable(
    address_block_api_tzkt, address_block_api_tzpro, address_block_api_rpc
):
    assert address_block_api_tzkt.get_delegatable(
        MAINNET_ADDRESS_STAKENOW_BAKER
    ) == address_block_api_tzpro.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)
    assert address_block_api_tzkt.get_delegatable(
        MAINNET_ADDRESS_STAKENOW_BAKER
    ) == address_block_api_rpc.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)
    assert address_block_api_tzpro.get_delegatable(
        MAINNET_ADDRESS_STAKENOW_BAKER
    ) == address_block_api_rpc.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)


# NOTE: We are using a testnet baker where we can manage the amount of delegates
@pytest.fixture
def address_reward_api_tzkt():
    return TzKTRewardApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
    )


@pytest.fixture
def address_reward_api_tzpro():
    return TzProRewardApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
        TZPRO_API_KEY,
    )


@pytest.fixture
def current_cycle_ghostnet():
    tip = "https://api.ghost.tzpro.io/explorer/tip"
    resp = requests.get(tip, timeout=5, headers={"X-API-Key": TZPRO_API_KEY})
    return int(resp.json()["cycle"])


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_rewards_for_cycle_map.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_rewards_for_cycle_map(
    address_reward_api_tzkt,
    address_reward_api_tzpro,
):
    # NOTE: There is currently a level limit query with rpc when querying endorsing rewards in the past
    # thus we are disabling the consistency check with other APIs for now but will hopefully reenable it in the future

    last_cycle = 689
    rewards_tzkt = address_reward_api_tzkt.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )
    rewards_tzpro = address_reward_api_tzpro.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )
    # Check total_reward_amount
    assert rewards_tzkt.total_reward_amount == rewards_tzpro.total_reward_amount

    # Check delegate_staking_balance
    assert (
        rewards_tzkt.delegate_staking_balance == rewards_tzpro.delegate_staking_balance
    )

    # Check delegator_balance_dict
    for (
        tzkt_delegator_adress,
        tzkt_balance_dict,
    ) in rewards_tzkt.delegator_balance_dict.items():
        if MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT == tzkt_delegator_adress:
            continue

        tzpro_balance = rewards_tzpro.delegator_balance_dict.get(
            tzkt_delegator_adress,
        )
        assert tzkt_balance_dict["current_balance"] == pytest.approx(
            tzpro_balance["current_balance"],
            1,
        )
        assert tzkt_balance_dict["staking_balance"] == pytest.approx(
            tzpro_balance["staking_balance"],
            1,
        )

    # Check num_baking_rights
    assert rewards_tzkt.num_baking_rights == rewards_tzpro.num_baking_rights

    # Check denunciation_rewards
    assert rewards_tzkt.denunciation_rewards == rewards_tzpro.denunciation_rewards

    # Check equivocation_losses
    assert rewards_tzkt.equivocation_losses == rewards_tzpro.equivocation_losses

    # Check offline_losses
    assert rewards_tzkt.offline_losses == pytest.approx(
        rewards_tzpro.offline_losses, 60000
    )
    # Check potential_endorsement_rewards
    # TODO: tzpro total_active_stake does not match rpc and tzkt exactly thus the approximation
    assert rewards_tzkt.potential_endorsement_rewards == pytest.approx(
        rewards_tzpro.potential_endorsement_rewards, 60000
    )
    # Check rewards_and_fees
    assert rewards_tzkt.rewards_and_fees == rewards_tzpro.rewards_and_fees

    # Check computed_reward_amount
    assert rewards_tzkt.computed_reward_amount == rewards_tzpro.computed_reward_amount
