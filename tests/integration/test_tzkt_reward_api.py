import unittest
import pytest
from unittest.mock import patch, MagicMock
from Constants import (
    RewardsType,
    DEFAULT_NETWORK_CONFIG_MAP,
    RPC_PUBLIC_API_URL,
    MAX_SEQUENT_CALLS,
)
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzstats.tzstats_reward_api import TzStatsRewardApiImpl
from tzkt.tzkt_reward_api import TzKTRewardApiImpl, RewardLog
from tzkt.tzkt_api import TzKTApiError
from parameterized import parameterized
from tests.utils import load_reward_model, store_reward_model, Constants

STAKENOW_ADDRESS = Constants.STAKENOW_ADDRESS
CYCLE = 100

"""
These tests are cached. To re-run, delete contents of the tzkt_data folder.
"""

dummy_addr_dict = dict(
    pkh="pkh",
    originated=False,
    alias="alias",
    sk="secret_key",
    manager="manager",
    revealed=True,
)


@patch("rpc.rpc_reward_api.sleep", MagicMock())
@patch("rpc.rpc_reward_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
class RewardApiImplTests(unittest.TestCase):
    def assertBalancesAlmostEqual(self, expected: dict, actual: dict, delta=1):
        for address, balances in expected.items():
            self.assertIn(address, actual, msg=f"{address} is missing")
            self.assertAlmostEqual(
                balances["staking_balance"],
                actual[address]["staking_balance"],
                delta=delta,
                msg=address,
            )

    @parameterized.expand(
        [
            ("tz1ZRWFLgT9sz8iFi1VYWPfRYeUvUSFAaDao", 201),
            ("tz1Lhf4J9Qxoe3DZ2nfe8FGDnvVj7oKjnMY6", 185),  # double baking (loss)
            ("tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8", 74),  # double baking (gain)
            ("tz1PeZx7FXy7QRuMREGXGxeipb24RsMMzUNe", 135),  # double endorsement (loss)
            ("tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA", 135),  # double endorsement (gain)
            ("tz1S1Aew75hMrPUymqenKfHo8FspppXKpW7h", 233),  # revelation rewards
            ("tz1UUgPwikRHW1mEyVZfGYy6QaxrY6Y7WaG5", 207),  # revelation miss
        ]
    )
    def test_get_rewards_for_cycle_map(self, address, cycle):
        """
        This test compares the total rewards and balance according to tzkt,
        to the total rewards according to rpc.

        It also compares the balances per delegator.
        """
        rpc_rewards = load_reward_model(address, cycle, "actual", dir_name="tzkt_data")
        if rpc_rewards is None:
            rpc_impl = RpcRewardApiImpl(
                nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
                baking_address=address,
                node_url=RPC_PUBLIC_API_URL["MAINNET"],
            )
            rpc_rewards = rpc_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)
            store_reward_model(
                address, cycle, "actual", rpc_rewards, dir_name="tzkt_data"
            )

        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
        )
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        self.assertAlmostEqual(
            rpc_rewards.delegate_staking_balance,
            tzkt_rewards.delegate_staking_balance,
            delta=1,
        )
        self.assertAlmostEqual(
            rpc_rewards.total_reward_amount, tzkt_rewards.total_reward_amount, delta=1
        )
        self.assertBalancesAlmostEqual(
            rpc_rewards.delegator_balance_dict,
            tzkt_rewards.delegator_balance_dict,
            delta=1,
        )

    @parameterized.expand(
        [
            ("tz1YKh8T79LAtWxX29N5VedCSmaZGw9LNVxQ", 246),
            ("tz1ZRWFLgT9sz8iFi1VYWPfRYeUvUSFAaDao", 232),  # missed endorsements
            ("tz1S8e9GgdZG78XJRB3NqabfWeM37GnhZMWQ", 235),  # low-priority endorsements
            ("tz1RV1MBbZMR68tacosb7Mwj6LkbPSUS1er1", 242),  # missed blocks
            ("tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8", 233),  # stolen blocks
        ]
    )
    def test_expected_rewards(self, address, cycle):
        tzstats_rewards = load_reward_model(address, cycle, "expected")
        if tzstats_rewards is None:
            tzstats_impl = TzStatsRewardApiImpl(
                nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
            )
            tzstats_rewards = tzstats_impl.get_rewards_for_cycle_map(
                cycle, RewardsType.ESTIMATED
            )
            store_reward_model(address, cycle, "expected", tzstats_rewards)

        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
        )
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ESTIMATED)

        self.assertAlmostEqual(
            tzstats_rewards.delegate_staking_balance,
            tzkt_rewards.delegate_staking_balance,
            delta=1,
        )
        self.assertAlmostEqual(
            tzstats_rewards.total_reward_amount,
            tzkt_rewards.total_reward_amount,
            delta=1,
        )
        self.assertBalancesAlmostEqual(
            tzstats_rewards.delegator_balance_dict,
            tzkt_rewards.delegator_balance_dict,
            delta=1,
        )

    def test_staking_balance_issue(self):
        address = "tz1V4qCyvPKZ5UeqdH14HN42rxvNPQfc9UZg"
        cycle = 220  # snapshot index == 15

        rpc_rewards = load_reward_model(address, cycle, "actual")
        if rpc_rewards is None:
            rpc_impl = RpcRewardApiImpl(
                nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
                baking_address=address,
                node_url=RPC_PUBLIC_API_URL["MAINNET"],
            )
            rpc_rewards = rpc_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)
            store_reward_model(address, cycle, "actual", rpc_rewards)

        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
        )
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        self.assertAlmostEqual(
            rpc_rewards.delegate_staking_balance, tzkt_rewards.delegate_staking_balance
        )
        self.assertAlmostEqual(
            rpc_rewards.total_reward_amount, tzkt_rewards.total_reward_amount, delta=1
        )

    def test_update_current_balances(self):
        log_items = [
            RewardLog(
                address="KT1Np1h72jGkRkfxNHLXNNJLHNbj9doPz4bR",
                type="D",
                staking_balance=100500,
                current_balance=0,
            )
        ]
        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
            baking_address="tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA",
        )
        tzkt_impl.update_current_balances(log_items)
        self.assertNotEqual(0, log_items[0].current_balance)


@pytest.fixture
def address_api():
    return TzKTRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=STAKENOW_ADDRESS
    )


class Mock_404_Response:
    def json(self):
        return None

    @property
    def status_code(self):
        return 404

    @property
    def text(self):
        return "404 Error happened"


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=Mock_404_Response()),
)
@patch("tzkt.tzkt_api.sleep", MagicMock())
@patch("tzkt.tzkt_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_tzkt_terminate_404(address_api):
    with pytest.raises(
        TzKTApiError,
        match="TzKT returned 404 error:\n404 Error happened",
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )


class Mock_500_Response:
    def json(self):
        return {}

    @property
    def status_code(self):
        return 500

    @property
    def text(self):
        return "500 BAD REQUEST"


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=Mock_500_Response()),
)
@patch("tzkt.tzkt_api.sleep", MagicMock())
@patch("tzkt.tzkt_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_tzkt_retry_500(address_api):
    with pytest.raises(
        TzKTApiError,
        match=r"Max sequent calls number exceeded \({}\)".format(MAX_SEQUENT_CALLS),
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )


class Mock_204_Response:
    def json(self):
        return {}

    @property
    def status_code(self):
        return 204

    @property
    def text(self):
        return "204 NO CONTENT"


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=Mock_204_Response()),
)
@patch("tzkt.tzkt_api.sleep", MagicMock())
@patch("tzkt.tzkt_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_tzkt_retry_204(address_api):
    with pytest.raises(
        TzKTApiError,
        match=r"Max sequent calls number exceeded \({}\)".format(MAX_SEQUENT_CALLS),
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
