import os
import vcr
import pytest
from src.blockwatch.tzpro_reward_api import TzProRewardApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP, RewardsType
from tests.utils import Constants
from src.exception.api_provider import ApiProviderException

MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
CYCLE = 100


@pytest.fixture
def address_api():
    return TzProRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=MAINNET_ADDRESS_STAKENOW_BAKER,
        tzpro_api_key=os.environ.get("TZPRO_API_KEY"),
    )


@pytest.fixture
def not_existent_address_api():
    return TzProRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address="tzxxxxxxxxx",
        tzpro_api_key=os.environ.get("TZPRO_API_KEY"),
    )


@patch(
    "blockwatch.tzpro_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print))
)
@vcr.use_cassette(
    "tests/integration/cassettes/tzpro_api/test_get_rewards_for_cycle_map.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_rewards_for_cycle_map(address_api):
    rewards = address_api.get_rewards_for_cycle_map(
        cycle=CYCLE, rewards_type=RewardsType.ACTUAL
    )
    assert rewards.delegate_staking_balance == 162719327201
    assert rewards.total_reward_amount == 123000000
    assert len(rewards.delegator_balance_dict) == 19


@vcr.use_cassette(
    "tests/integration/cassettes/tzpro_api/test_tzpro_terminate_400.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_tzpro_terminate_400(not_existent_address_api):
    with pytest.raises(
        Exception,
        match=r"GET https://api.tzpro.io/tables/income\?address=tzxxxxxxxxx&cycle=100 400",
    ):
        _ = not_existent_address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
