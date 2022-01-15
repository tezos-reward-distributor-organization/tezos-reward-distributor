import unittest
import os
import json
from typing import Optional
from unittest.mock import patch, MagicMock
from os.path import dirname, join

from Constants import RewardsType, DEFAULT_NETWORK_CONFIG_MAP, RPC_PUBLIC_API_URL
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzstats.tzstats_reward_api import TzStatsRewardApiImpl, RewardProviderModel
from tzkt.tzkt_reward_api import TzKTRewardApiImpl, RewardLog
from parameterized import parameterized

"""
These tests are cached. To re-run, delete contents of the tzkt_data folder.
"""


def load_reward_model(
    address, cycle, suffix, dir_name="tzkt_data"
) -> Optional[RewardProviderModel]:
    path = join(dirname(__file__), f"{dir_name}/{address}_{cycle}_{suffix}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            data = json.loads(f.read())
        return RewardProviderModel(
            delegate_staking_balance=data["delegate_staking_balance"],
            total_reward_amount=data["total_reward_amount"],
            rewards_and_fees=data["rewards_and_fees"],
            equivocation_losses=data["equivocation_losses"],
            offline_losses=data["offline_losses"],
            num_baking_rights=data["num_baking_rights"],
            num_endorsing_rights=data["num_endorsing_rights"],
            denunciation_rewards=data["denunciation_rewards"],
            delegator_balance_dict=data["delegator_balance_dict"],
            computed_reward_amount=None,
        )
    else:
        return None


def store_reward_model(
    address, cycle, suffix, model: RewardProviderModel, dir_name="tzkt_data"
):
    path = join(dirname(__file__), f"{dir_name}/{address}_{cycle}_{suffix}.json")
    data = dict(
        delegate_staking_balance=model.delegate_staking_balance,
        total_reward_amount=model.total_reward_amount,
        rewards_and_fees=model.rewards_and_fees,
        equivocation_losses=model.equivocation_losses,
        offline_losses=model.offline_losses,
        num_baking_rights=model.num_baking_rights,
        num_endorsing_rights=model.num_endorsing_rights,
        denunciation_rewards=model.denunciation_rewards,
        delegator_balance_dict={
            k: {i: v[i] for i in v if i != "current_balance"}
            for k, v in model.delegator_balance_dict.items()
            if v["staking_balance"] > 0
        },
    )
    try:
        with open(path, "w+") as f:
            f.write(json.dumps(data, indent=2))
    except Exception as e:
        import errno

        print("Exception during write operation invoked: {}".format(e))
        if e.errno == errno.ENOSPC:
            print("Not enough space on device!")
        exit()


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
