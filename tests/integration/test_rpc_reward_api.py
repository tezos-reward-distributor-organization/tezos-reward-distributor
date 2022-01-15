import pytest
from rpc.rpc_reward_api import RpcRewardApiImpl
from unittest.mock import patch, MagicMock
from Constants import RPC_PUBLIC_API_URL, DEFAULT_NETWORK_CONFIG_MAP, RewardsType
from tests.integration.test_tzkt_reward_api import load_reward_model, store_reward_model
from exception.api_provider import ApiProviderException
from tests.utils import Constants

STAKENOW_ADDRESS = Constants.STAKENOW_ADDRESS
CYCLE = 100


@pytest.fixture
def address_api():
    return RpcRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=STAKENOW_ADDRESS,
        node_url=RPC_PUBLIC_API_URL["MAINNET"],
    )


@patch("rpc.rpc_reward_api.sleep", MagicMock())
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_get_rewards_for_cycle_map(address_api):
    rewards = load_reward_model(STAKENOW_ADDRESS, CYCLE, "actual", dir_name="rpc_data")
    if rewards is None:
        rewards = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
        store_reward_model(
            STAKENOW_ADDRESS, CYCLE, "actual", rewards, dir_name="rpc_data"
        )
    assert rewards.delegate_staking_balance == 162719327201
    assert rewards.total_reward_amount == 123000000
    assert len(rewards.delegator_balance_dict) == 20


class Mock_404_Response:
    def json(self):
        return None

    @property
    def status_code(self):
        return 404


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_404_Response()),
)
@patch("rpc.rpc_reward_api.sleep", MagicMock())
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_rpc_terminate_404(address_api):

    with pytest.raises(
        ApiProviderException,
        match="RPC URL 'https://rpc.tzkt.io/mainnet/chains/main/blocks/head' not found. Is this node in archive mode?",
    ):
        rewards = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_404_Response()),
)
@patch("rpc.rpc_reward_api.sleep", MagicMock())
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_rpc_contract_storage(address_api):
    with pytest.raises(
        ApiProviderException,
        match="RPC URL 'https://rpc.tzkt.io/mainnet/chains/main/blocks/head/context/contracts/KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU/storage' not found. Is this node in archive mode?",
    ):
        contract_storage = address_api.get_contract_storage(
            contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block="head"
        )
