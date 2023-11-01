import pytest
from src.blockwatch.tzpro_reward_api import TzProRewardApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP, RewardsType
from tests.utils import load_reward_model, store_reward_model, Constants
from exception.api_provider import ApiProviderException

MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
CYCLE = 100


@pytest.fixture
def address_api():
    return TzProRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=MAINNET_ADDRESS_STAKENOW_BAKER,
    )


@patch(
    "blockwatch.tzpro_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print))
)
def test_get_rewards_for_cycle_map(address_api):
    rewards = load_reward_model(
        MAINNET_ADDRESS_STAKENOW_BAKER,
        CYCLE,
        RewardsType.ACTUAL,
        dir_name="tzpro_data",
    )
    if rewards is None:
        rewards = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
        store_reward_model(
            MAINNET_ADDRESS_STAKENOW_BAKER,
            CYCLE,
            RewardsType.ACTUAL,
            rewards,
            dir_name="tzpro_data",
        )
    assert rewards.delegate_staking_balance == 162719327201
    assert rewards.total_reward_amount == 123000000
    assert len(rewards.delegator_balance_dict) == 19


class Mock_404_Response:
    def json(self):
        return None

    @property
    def content(self):
        return "No content!".encode()

    @property
    def status_code(self):
        return 404


@patch(
    "src.blockwatch.tzpro_reward_provider_helper.requests.get",
    MagicMock(return_value=Mock_404_Response()),
)
def test_tzpro_terminate_404(address_api):

    with pytest.raises(
        ApiProviderException,
        match=r"GET https://api.tzpro.io/tables/income\?address=tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194&cycle=100 404",
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
