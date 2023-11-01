import unittest
import pytest
from unittest.mock import patch, MagicMock
from src.Constants import (
    RewardsType,
    DEFAULT_NETWORK_CONFIG_MAP,
    PUBLIC_NODE_URL,
    MAX_SEQUENT_CALLS,
)
from src.rpc.rpc_reward_api import RpcRewardApiImpl
from src.blockwatch.tzpro_reward_api import TzProRewardApiImpl
from src.tzkt.tzkt_reward_api import TzKTRewardApiImpl, RewardLog
from src.tzkt.tzkt_api import TzKTApiError
from parameterized import parameterized
from tests.utils import load_reward_model, store_reward_model, Constants

MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
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
    def assertBalancesAlmostEqual(self, expected: dict, actual: dict, delta=0):
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
            ("tz1NRGxXV9h6SdNaZLcgmjuLx3hyy2f8YoGN", 520),
            ("tz1MbhmEwEAzzfb3naSr7vTp4mDxB8HsknA9", 510),
            ("tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8", 500),
            ("tz1V4qCyvPKZ5UeqdH14HN42rxvNPQfc9UZg", 500),
            ("tz1MbhmEwEAzzfb3naSr7vTp4mDxB8HsknA9", 490),
            ("tz1Lhf4J9Qxoe3DZ2nfe8FGDnvVj7oKjnMY6", 480),
            (
                "tz1MbhmEwEAzzfb3naSr7vTp4mDxB8HsknA9",
                475,
            ),  # staking balance difference 8605284 Mutez between tzkt and pRPC
        ]
    )
    def test_get_rewards_for_cycle_map(self, address, cycle):
        """
        This test compares the total rewards and balance according to tzkt,
        to the total rewards according to rpc.
        It also compares the balances per delegator.
        Currently only tests with RPC work above the tenderbake update.
        Meaning snapshots above cycle 468.
        """
        rpc_rewards = load_reward_model(
            address, cycle, RewardsType.ACTUAL, dir_name="rpc_data"
        )
        if rpc_rewards is None:
            rpc_impl = RpcRewardApiImpl(
                nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
                baking_address=address,
                node_url=PUBLIC_NODE_URL["MAINNET"],
            )
            rpc_rewards = rpc_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)
            store_reward_model(
                address, cycle, RewardsType.ACTUAL, rpc_rewards, dir_name="rpc_data"
            )

        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
        )
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        # TODO: Investigate why rpc staking balance is not equal to tzpro or tzkt below the tenderbake protocol
        staking_balance_delta = 8605284 if cycle < 475 else 0
        self.assertAlmostEqual(
            rpc_rewards.delegate_staking_balance + staking_balance_delta,
            tzkt_rewards.delegate_staking_balance,
            delta=0,
        )
        self.assertBalancesAlmostEqual(
            rpc_rewards.delegator_balance_dict,
            tzkt_rewards.delegator_balance_dict,
            delta=0,
        )
        # FIXME: Currently the rpc baking_rights cannot be queried (429 error)
        # thus we skip the reward and baking_rights sanity checks
        # self.assertAlmostEqual(
        #     rpc_rewards.num_baking_rights,
        #     tzkt_rewards.num_baking_rights,
        #     delta=0,
        # )
        # self.assertAlmostEqual(
        #     rpc_rewards.total_reward_amount, tzkt_rewards.total_reward_amount, delta=0
        # )

    @parameterized.expand(
        [
            ("tz1NRGxXV9h6SdNaZLcgmjuLx3hyy2f8YoGN", 520),
            ("tz1MbhmEwEAzzfb3naSr7vTp4mDxB8HsknA9", 510),
            ("tz1YKh8T79LAtWxX29N5VedCSmaZGw9LNVxQ", 246),
            ("tz1ZRWFLgT9sz8iFi1VYWPfRYeUvUSFAaDao", 232),  # missed endorsements
            ("tz1S8e9GgdZG78XJRB3NqabfWeM37GnhZMWQ", 235),  # low-priority endorsements
            ("tz1RV1MBbZMR68tacosb7Mwj6LkbPSUS1er1", 242),  # missed blocks
            ("tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8", 233),  # stolen blocks
        ]
    )
    def test_expected_rewards(self, address, cycle):
        tzpro_rewards = load_reward_model(
            address, cycle, "actual", dir_name="tzpro_data"
        )
        if tzpro_rewards is None:
            tzpro_impl = TzProRewardApiImpl(
                nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
            )
            tzpro_rewards = tzpro_impl.get_rewards_for_cycle_map(
                cycle, RewardsType.ACTUAL
            )
            store_reward_model(
                address, cycle, "actual", tzpro_rewards, dir_name="tzpro_data"
            )

        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
        )
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        self.assertAlmostEqual(
            tzpro_rewards.delegate_staking_balance,
            tzkt_rewards.delegate_staking_balance,
            delta=0,
        )
        self.assertAlmostEqual(
            tzpro_rewards.total_reward_amount,
            tzkt_rewards.total_reward_amount,
            delta=0,
        )
        self.assertAlmostEqual(
            tzpro_rewards.num_baking_rights,
            tzkt_rewards.num_baking_rights,
            delta=0,
        )
        self.assertBalancesAlmostEqual(
            tzpro_rewards.delegator_balance_dict,
            tzkt_rewards.delegator_balance_dict,
            delta=0,
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
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=MAINNET_ADDRESS_STAKENOW_BAKER,
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
