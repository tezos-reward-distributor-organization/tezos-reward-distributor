import pytest
from rpc.rpc_reward_api import RpcRewardApiImpl
from unittest.mock import patch, MagicMock
from Constants import (
    PUBLIC_NODE_URL,
    DEFAULT_NETWORK_CONFIG_MAP,
    RewardsType,
    MAX_SEQUENT_CALLS,
)
from tests.utils import load_reward_model, store_reward_model, Constants
from exception.api_provider import ApiProviderException
from requests.exceptions import RequestException

STAKENOW_ADDRESS = Constants.STAKENOW_ADDRESS
CYCLE = 100


@pytest.fixture
def address_api():
    return RpcRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=STAKENOW_ADDRESS,
        node_url=PUBLIC_NODE_URL["MAINNET"],
    )



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
        match="RPC URL '{}/chains/main/blocks/head' not found. Is this node in archive mode?".format(
            PUBLIC_NODE_URL["MAINNET"]
        ),
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )




ERROR_MESSAGE_500 = "500 INTERNAL SERVER ERROR!"


class Mock_500_Response:
    def json(self):
        raise RequestException(ERROR_MESSAGE_500)

    @property
    def status_code(self):
        return 500
