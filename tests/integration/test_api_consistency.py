import os
import pytest
import vcr
import requests
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP, PUBLIC_NODE_URL, RewardsType
from tests.utils import Constants

# Block APIs
from src.tzkt.tzkt_block_api import TzKTBlockApiImpl

# Reward APIs
from src.tzkt.tzkt_reward_api import TzKTRewardApiImpl

MAINNET_ADDRESS_DELEGATOR = Constants.MAINNET_ADDRESS_DELEGATOR
MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
MAINNET_ADDRESS_BAKEXTZ4ME_BAKER = Constants.MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
GHOSTNET_ADDRESS_STAKENOW_BAKER = Constants.GHOSTNET_ADDRESS_STAKENOW_BAKER
MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT = Constants.MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT

# These tests should not be mocked but test the overall consistency
# accross all tezos APIs which are available in TRD


@pytest.fixture
def address_block_api_tzkt():
    return TzKTBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_revelation.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_revelation(address_block_api_tzkt):
    assert address_block_api_tzkt.get_revelation(MAINNET_ADDRESS_DELEGATOR)


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_current_cycle_and_level.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_current_cycle_and_level(address_block_api_tzkt):
    cycle_tzkt, level_tzkt = address_block_api_tzkt.get_current_cycle_and_level()

    assert cycle_tzkt == 751


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_delegatable.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_delegatable(address_block_api_tzkt):
    assert address_block_api_tzkt.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)


# NOTE: We are using a testnet baker where we can manage the amount of delegates
@pytest.fixture
def address_reward_api_tzkt():
    return TzKTRewardApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
    )


@vcr.use_cassette(
    "tests/integration/cassettes/api_consistency/test_get_rewards_for_cycle_map.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_rewards_for_cycle_map(
    address_reward_api_tzkt,
):
    # NOTE: There is currently a level limit query with rpc when querying endorsing rewards in the past
    # thus we are disabling the consistency check with other APIs for now but will hopefully reenable it in the future

    last_cycle = 750
    rewards_tzkt = address_reward_api_tzkt.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )

    # Check delegator_balance_dict
    for (
        tzkt_delegator_adress,
        tzkt_balance_dict,
    ) in rewards_tzkt.delegator_balance_dict.items():
        if MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT == tzkt_delegator_adress:
            continue

        assert tzkt_balance_dict["current_balance"] == 0
        assert tzkt_balance_dict["delegating_balance"] == 257

    # Check num_baking_rights
    assert rewards_tzkt.num_baking_rights == 0

    # Check denunciation_rewards
    assert rewards_tzkt.denunciation_rewards == 0

    # Check equivocation_losses
    assert rewards_tzkt.equivocation_losses == 0

    # Check offline_losses
    assert rewards_tzkt.offline_losses == 0
    # Check potential_endorsement_rewards
    # TODO: tzpro total_active_stake does not match rpc and tzkt exactly thus the approximation
    assert rewards_tzkt.potential_endorsement_rewards == 0
    # Check rewards_and_fees
    assert rewards_tzkt.rewards_and_fees == 0

    # Check computed_reward_amount
    assert rewards_tzkt.computed_reward_amount == 0
