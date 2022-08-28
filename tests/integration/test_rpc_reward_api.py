import pytest
from http import HTTPStatus
from rpc.rpc_reward_api import RpcRewardApiImpl
from unittest.mock import patch, MagicMock
from Constants import (
    PUBLIC_NODE_URL,
    DEFAULT_NETWORK_CONFIG_MAP,
    MAX_SEQUENT_CALLS,
    RewardsType,
)
from tests.utils import load_reward_model, store_reward_model, Constants
from exception.api_provider import ApiProviderException
from requests.exceptions import RequestException

# Use this baker because he has < 40 delegates which can be fetched fast
BAKEXTZ4ME_ADDRESS = Constants.BAKEXTZ4ME_ADDRESS
CYCLE = 515


@pytest.fixture
def address_api():
    return RpcRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=BAKEXTZ4ME_ADDRESS,
        node_url=PUBLIC_NODE_URL["MAINNET"],
    )


@patch("rpc.rpc_reward_api.sleep", MagicMock())
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_get_rewards_for_cycle_map(address_api):
    rewards = load_reward_model(
        BAKEXTZ4ME_ADDRESS, CYCLE, RewardsType.ACTUAL, dir_name="rpc_data"
    )
    if rewards is None:
        rewards = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
        store_reward_model(
            BAKEXTZ4ME_ADDRESS, CYCLE, RewardsType.ACTUAL, rewards, dir_name="rpc_data"
        )
    assert rewards.delegate_staking_balance == 80573814172
    assert rewards.total_reward_amount == 59192613
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
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block=2500000
    )
    assert contract_storage["string"] == "tz1SvJLCJ1kKP5zVNnoSwVUAuW7dP9HEExE3"


def test_rpc_contract_balance(address_api):
    contract_balance = address_api.get_contract_balance(
        contract_id="KT1XmgW5Pqpy9CMBEoNU9qmpnM8UVVaeyoXU", block=2500000
    )
    assert contract_balance == 9087234


def test_get_stake_snapshot_block_level(address_api):
    stake_snapshot, level_snapshot_block = address_api.get_stake_snapshot_block_level(
        500, 2500000
    )
    assert stake_snapshot == 6
    assert level_snapshot_block == 2461184

    stake_snapshot, level_snapshot_block = address_api.get_stake_snapshot_block_level(
        474, 2300000
    )
    assert stake_snapshot == 15
    assert level_snapshot_block == 2252800

    stake_snapshot, level_snapshot_block = address_api.get_stake_snapshot_block_level(
        470, 2300000
    )
    assert stake_snapshot == 0
    assert level_snapshot_block == 2244608


# TODO: If a test needs to be diabled because of an unsolvable API issue
# please use pytest.mark.skip and give an understandable reason for that
# @pytest.mark.skip(reason="no way of currently testing this")
def test_get_baking_rights(address_api):
    backing_rights = address_api.get_baking_rights(518, 2661200)
    for backing_right in backing_rights:
        backing_right["delegate"] == BAKEXTZ4ME_ADDRESS
        backing_right["level"] in [2659190, 2659240, 2660797, 2662063]


def test_get_potential_endorsement_rewards(address_api):
    potential_endorsement_rewards = address_api.get_potential_endorsement_rewards(
        518, 2661200
    )
    assert potential_endorsement_rewards == 19336176


def test_get_block_data(address_api):
    (
        author,
        payload_proposer,
        reward_and_fees,
        bonus,
        double_signing_reward,
    ) = address_api.get_block_data(2661200)

    assert author == "tz1gfArv665EUkSg2ojMBzcbfwuPxAvqPvjo"
    assert payload_proposer == "tz1gfArv665EUkSg2ojMBzcbfwuPxAvqPvjo"
    assert reward_and_fees == 10024764
    assert bonus == 9956378
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
                    "contract": BAKEXTZ4ME_ADDRESS,
                    "change": "500",
                    "origin": "block",
                },
                {
                    "kind": "burned",
                    "category": "lost endorsing rewards",
                    "contract": BAKEXTZ4ME_ADDRESS,
                    "change": "-9956378",
                    "origin": "block",
                },
            ]
        }

    @property
    def status_code(self):
        return 200


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
        return 200


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_Current_Balance_Response()),
)
def test_get_current_balance_of_delegator(address_api):
    assert 1234567 == address_api.get_current_balance_of_delegator(BAKEXTZ4ME_ADDRESS)


@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_get_delegators_and_delgators_balances(address_api):
    (
        delegate_staking_balance,
        delegators,
    ) = address_api.get_delegators_and_delgators_balances(518, 2661200)
    assert 80605630975 == delegate_staking_balance

    sum_delegators_stake = 0
    for delegator, delegator_balance in delegators.items():
        sum_delegators_stake += delegator_balance["staking_balance"]
    assert 69507505710 == sum_delegators_stake


class Mock_Current_Level_Response:
    def json(self):
        return {"metadata": {"level_info": {"level": 2662060, "cycle": 518}}}

    @property
    def status_code(self):
        return 200


@patch(
    "src.rpc.rpc_reward_api.requests.get",
    MagicMock(return_value=Mock_Current_Level_Response()),
)
def test_get_current_level(address_api):
    current_level, current_cycle = address_api.get_current_level()
    assert 2662060 == current_level
    assert 518 == current_cycle
