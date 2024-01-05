import pytest
import vcr
from http import HTTPStatus
from src.rpc.rpc_reward_api import RpcRewardApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import (
    PUBLIC_NODE_URL,
    DEFAULT_NETWORK_CONFIG_MAP,
    MAX_SEQUENT_CALLS,
    RewardsType,
)
from tests.utils import load_reward_model, store_reward_model, Constants
from src.exception.api_provider import ApiProviderException
from requests.exceptions import RequestException

# Use this baker because he has < 40 delegates which can be fetched fast
MAINNET_ADDRESS_BAKEXTZ4ME_BAKER = Constants.MAINNET_ADDRESS_BAKEXTZ4ME_BAKER


@pytest.fixture
def address_api():
    return RpcRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
        node_url=PUBLIC_NODE_URL["MAINNET"],
    )


@patch("src.rpc.rpc_reward_api.sleep", MagicMock())
@patch("src.rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_rewards_for_cycle_map.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_rewards_for_cycle_map(address_api):
    cycle = 689
    rewards = address_api.get_rewards_for_cycle_map(
        cycle=cycle, rewards_type=RewardsType.ACTUAL
    )
    assert rewards.delegate_staking_balance == 77965234131
    assert rewards.total_reward_amount == 19935448
    assert len(rewards.delegator_balance_dict) == 34


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_rpc_terminate_404.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
@patch("src.rpc.rpc_reward_api.sleep", MagicMock())
@patch("src.rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_rpc_terminate_404(address_api):
    current_cycle = 660

    with pytest.raises(
        Exception,
        match="RPC URL '{}/chains/main/blocks/4873991/context/raw/json/cycle/660/total_active_stake' not found. Is this node in archive mode?".format(
            PUBLIC_NODE_URL["MAINNET"]
        ),
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=current_cycle, rewards_type=RewardsType.ACTUAL
        )


ERROR_MESSAGE_500 = "500 INTERNAL SERVER ERROR!"


class Mock_500_Response:
    def json(self):
        raise RequestException(ERROR_MESSAGE_500)

    @property
    def status_code(self):
        return 500


@patch("src.rpc.rpc_reward_api.sleep", MagicMock())
@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_500_Response()),
)
@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_rpc_contract_storage_500.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_rpc_contract_storage_500(address_api, caplog):
    # This test will retry to get_contract_storage 256 times
    # defined by the MAX_SEQUENT_CALLS in the constants
    contract_storage = address_api.get_contract_storage(
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block="head"
    )
    assert contract_storage is None
    assert (
        "Failed with exception, will retry (1) : {}".format(ERROR_MESSAGE_500)
        in caplog.text
    )
    assert (
        "Failed with exception, will retry ({}) : {}".format(
            MAX_SEQUENT_CALLS, ERROR_MESSAGE_500
        )
        in caplog.text
    )


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_rpc_contract_storage.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_rpc_contract_storage(address_api):
    # API call to test the storage account
    contract_storage = address_api.get_contract_storage(
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block="head"
    )
    assert contract_storage["string"] == "tz1SvJLCJ1kKP5zVNnoSwVUAuW7dP9HEExE3"


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_rpc_contract_balance.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_rpc_contract_balance(address_api):
    contract_balance = address_api.get_contract_balance(
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block="head"
    )
    assert contract_balance == 9484475


# TODO: If a test needs to be disabled because of an unsolvable API issue
# please use pytest.mark.skip and give an understandable reason for that
# @pytest.mark.skip(reason="no way of currently testing this")
@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_baking_rights.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_baking_rights(address_api):
    _, current_cycle = address_api.get_current_level()
    all_baking_rights = address_api.get_all_baking_rights_cycle(current_cycle)
    first_baking_right = all_baking_rights[0]
    baking_rights = address_api.get_baking_rights(
        current_cycle, first_baking_right["delegate"]
    )

    assert baking_rights[0]["delegate"] == first_baking_right["delegate"]
    assert baking_rights[0]["level"] == first_baking_right["level"]


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_block_data.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_block_data(address_api):
    (
        author,
        payload_proposer,
        reward_and_fees,
        bonus,
        double_signing_reward,
    ) = address_api.get_block_data(4874002)
    assert author == "tz1ei4WtWEMEJekSv8qDnu9PExG6Q8HgRGr3"
    assert payload_proposer == "tz1ei4WtWEMEJekSv8qDnu9PExG6Q8HgRGr3"
    assert reward_and_fees == 5007339
    assert bonus == 4834608
    assert double_signing_reward == 0


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_endorsing_rewards.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_endorsing_rewards(address_api):
    endorsing_rewards, lost_endorsing_rewards = address_api.get_endorsing_rewards(
        2661200
    )
    assert 0 == endorsing_rewards
    assert 0 == lost_endorsing_rewards


class Mock_Endorsing_Reward_Response:
    def json(self):
        return {
            "balance_updates": [
                {
                    "kind": "accumulator",
                    "category": "block fees",
                    "change": "-24764",
                    "origin": "block",
                },
                {
                    "kind": "minted",
                    "category": "endorsing rewards",
                    "change": "-500",
                    "origin": "block",
                },
                {
                    "kind": "contract",
                    "contract": MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
                    "change": "500",
                    "origin": "block",
                },
                {
                    "kind": "burned",
                    "category": "lost endorsing rewards",
                    "contract": MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
                    "change": "-9956378",
                    "origin": "block",
                },
            ]
        }

    @property
    def status_code(self):
        return HTTPStatus.OK


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_Endorsing_Reward_Response()),
)
@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_endorsing_rewards_mocked.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_endorsing_rewards_mocked(address_api):
    endorsing_rewards, lost_endorsing_rewards = address_api.get_endorsing_rewards(
        2661200
    )
    assert 500 == endorsing_rewards
    assert -9956378 == lost_endorsing_rewards


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_current_balance_of_delegator.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_current_balance_of_delegator(address_api):
    assert 5023009232 == address_api.get_current_balance_of_delegator(
        MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
    )


# Check if delegator balance can be queried correctly
# Please do not mock up to detect any rpc api endpoint changes
@patch("src.rpc.rpc_reward_api.sleep", MagicMock())
@patch("src.rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_delegators_and_delgators_balances.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_delegators_and_delgators_balances(address_api):
    (
        delegate_staking_balance,
        delegators,
    ) = address_api.get_delegators_and_delgators_balances("head")
    assert isinstance(delegate_staking_balance, int)  # balance is an int

    sum_delegators_stake = 0
    for delegator, delegator_balance in delegators.items():
        sum_delegators_stake += delegator_balance["staking_balance"]
    assert isinstance(sum_delegators_stake, int)  # balance is an int


@vcr.use_cassette(
    "tests/integration/cassettes/rpc_api/test_get_current_level.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_current_level(address_api):
    current_level, current_cycle = address_api.get_current_level()
    assert 4873961 == current_level
    assert 690 == current_cycle
