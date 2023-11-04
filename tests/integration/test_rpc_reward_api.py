import pytest
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


class MockBlockData:
    def json(self):
        return {
            "protocol": "PtLimaPtLMwfNinJi9rCfDPWea8dFgTZ1MeJ9f1m2SRic6ayiwW",
            "chain_id": "NetXdQprcVkpaWU",
            "hash": "BMAtbi8QyyUKxqgmwevqXG27AHxz3WmiQgSpHVajnuL8osBmn6A",
            "header": {
                "level": 2984089,
                "proto": 15,
                "predecessor": "BKmonHxpafq9QyBBdVpipy1DWx3thHetxCDq7gGNiK7Uy7tdhRW",
                "timestamp": "2022-12-20T01:06:44Z",
                "validation_pass": 4,
                "operations_hash": "LLoZuteCN5WBeHBbFEM8qzoHBh8zxURP596KPPkw474HvEkhU372b",
                "fitness": [],
                "context": "CoVKmtZ8risGC68EFq8ATgwKeFaN8vSAnfcS8Uu5nq3i64wL6Cqo",
                "payload_hash": "vh2JpApDHYrGAJxFjoz5jW7iZdaUxeF7ApvJXAXyy7T386r2mpro",
            },
            "metadata": {
                "protocol": "PtLimaPtLMwfNinJi9rCfDPWea8dFgTZ1MeJ9f1m2SRic6ayiwW",
                "next_protocol": "PtLimaPtLMwfNinJi9rCfDPWea8dFgTZ1MeJ9f1m2SRic6ayiwW",
                "test_chain_status": {...},
                "max_operations_ttl": 120,
                "max_operation_data_length": 32768,
                "max_block_header_length": 289,
                "max_operation_list_length": [],
                "proposer": "tz1S8MNvuFEUsWgjHvi3AxibRBf388NhT1q2",
                "baker": "tz1S8MNvuFEUsWgjHvi3AxibRBf388NhT1q2",
                "balance_updates": [
                    {
                        "kind": "accumulator",
                        "category": "block fees",
                        "change": "-15710",
                        "origin": "block",
                    },
                    {
                        "kind": "minted",
                        "category": "baking rewards",
                        "change": "-10000000",
                        "origin": "block",
                    },
                    {
                        "kind": "contract",
                        "contract": "tz1S8MNvuFEUsWgjHvi3AxibRBf388NhT1q2",
                        "change": "10015710",
                        "origin": "block",
                    },
                    {
                        "kind": "minted",
                        "category": "baking bonuses",
                        "change": "-9617784",
                        "origin": "block",
                    },
                    {
                        "kind": "contract",
                        "contract": "tz1S8MNvuFEUsWgjHvi3AxibRBf388NhT1q2",
                        "change": "9617784",
                        "origin": "block",
                    },
                ],
            },
            "operations": [[], [], [], []],
        }

    @property
    def status_code(self):
        return HTTPStatus.OK


@pytest.fixture
def address_api():
    return RpcRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
        node_url=PUBLIC_NODE_URL["MAINNET"],
    )


@patch("rpc.rpc_reward_api.sleep", MagicMock())
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_get_rewards_for_cycle_map(address_api):
    cycle = 515
    rewards = load_reward_model(
        MAINNET_ADDRESS_BAKEXTZ4ME_BAKER, cycle, RewardsType.ACTUAL, dir_name="rpc_data"
    )
    if rewards is None:
        rewards = address_api.get_rewards_for_cycle_map(
            cycle=cycle, rewards_type=RewardsType.ACTUAL
        )
        store_reward_model(
            MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
            cycle,
            RewardsType.ACTUAL,
            rewards,
            dir_name="rpc_data",
        )
    assert rewards.delegate_staking_balance == 80573814172
    assert rewards.total_reward_amount == 19364746
    assert len(rewards.delegator_balance_dict) == 34


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
    current_cycle = 200

    with pytest.raises(
        Exception,
        match="RPC URL '{}/chains/main/blocks/head' not found. Is this node in archive mode?".format(
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


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_500_Response()),
)
@patch("rpc.rpc_reward_api.sleep", MagicMock())
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


def test_rpc_contract_storage(address_api):
    # API call to test the storage account
    contract_storage = address_api.get_contract_storage(
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block="head"
    )
    assert contract_storage["string"] == "tz1SvJLCJ1kKP5zVNnoSwVUAuW7dP9HEExE3"


class MockContractBalance:
    def json(self):
        return "9202886"

    @property
    def status_code(self):
        return HTTPStatus.OK


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=MockContractBalance()),
)
def test_rpc_contract_balance(address_api):
    contract_balance = address_api.get_contract_balance(
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block="head"
    )
    assert contract_balance == 9202886


# TODO: If a test needs to be disabled because of an unsolvable API issue
# please use pytest.mark.skip and give an understandable reason for that
# @pytest.mark.skip(reason="no way of currently testing this")
def test_get_baking_rights(address_api):
    _, current_cycle = address_api.get_current_level()
    all_baking_rights = address_api.get_all_baking_rights_cycle(current_cycle)
    first_baking_right = all_baking_rights[0]
    baking_rights = address_api.get_baking_rights(
        current_cycle, first_baking_right["delegate"]
    )

    assert baking_rights[0]["delegate"] == first_baking_right["delegate"]
    assert baking_rights[0]["level"] == first_baking_right["level"]


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=MockBlockData()),
)
def test_get_block_data(address_api):
    (
        author,
        payload_proposer,
        reward_and_fees,
        bonus,
        double_signing_reward,
    ) = address_api.get_block_data(2984089)

    assert author == "tz1S8MNvuFEUsWgjHvi3AxibRBf388NhT1q2"
    assert payload_proposer == "tz1S8MNvuFEUsWgjHvi3AxibRBf388NhT1q2"
    assert reward_and_fees == 10015710
    assert bonus == 9617784
    assert double_signing_reward == 0


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
def test_get_endorsing_rewards_mocked(address_api):
    endorsing_rewards, lost_endorsing_rewards = address_api.get_endorsing_rewards(
        2661200
    )
    assert 500 == endorsing_rewards
    assert -9956378 == lost_endorsing_rewards


class Mock_Current_Balance_Response:
    def json(self):
        return "1234567"

    @property
    def status_code(self):
        return HTTPStatus.OK


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_Current_Balance_Response()),
)
def test_get_current_balance_of_delegator(address_api):
    assert 1234567 == address_api.get_current_balance_of_delegator(
        MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
    )


# Check if delegator balance can be queried correctly
# Please do not mock up to detect any rpc api endpoint changes
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
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


class Mock_Current_Level_Response:
    def json(self):
        return {"metadata": {"level_info": {"level": 2662060, "cycle": 518}}}

    @property
    def status_code(self):
        return HTTPStatus.OK


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_Current_Level_Response()),
)
def test_get_current_level(address_api):
    current_level, current_cycle = address_api.get_current_level()
    assert 2662060 == current_level
    assert 518 == current_cycle
