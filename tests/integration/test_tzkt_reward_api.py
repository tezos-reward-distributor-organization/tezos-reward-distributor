import unittest
import os
import json
from typing import Optional
from unittest.mock import patch, MagicMock
from os.path import dirname, join

from Constants import RewardsType
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzstats.tzstats_reward_api import TzStatsRewardApiImpl, RewardProviderModel
from tzkt.tzkt_reward_api import TzKTRewardApiImpl, RewardLog
from NetworkConfiguration import default_network_config_map
from parameterized import parameterized


def load_reward_model(address, cycle, suffix) -> Optional[RewardProviderModel]:
    path = join(dirname(__file__), f'tzkt_data/{address}_{cycle}_{suffix}.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.loads(f.read())
        return RewardProviderModel(
            delegate_staking_balance=data['delegate_staking_balance'],
            total_reward_amount=data['total_reward_amount'],
            delegator_balance_dict=data['delegator_balance_dict'])
    else:
        return None


def store_reward_model(address, cycle, suffix, model: RewardProviderModel):
    path = join(dirname(__file__), f'tzkt_data/{address}_{cycle}_{suffix}.json')
    data = dict(
        delegate_staking_balance=model.delegate_staking_balance,
        total_reward_amount=model.total_reward_amount,
        delegator_balance_dict={
            k: v
            for k, v in model.delegator_balance_dict.items()
            if v['staking_balance'] > 0
        }
    )
    with open(path, 'w+') as f:
        f.write(json.dumps(data))


dummy_addr_dict = dict(
    pkh='pkh',
    originated=False,
    alias='alias',
    sk='secret_key',
    manager='manager',
    revealed=True
)


@patch('rpc.rpc_reward_api.sleep', MagicMock())
@patch('rpc.rpc_reward_api.logger', MagicMock(debug=MagicMock(side_effect=print)))
class RewardApiImplTests(unittest.TestCase):

    def assertBalancesAlmostEqual(self, expected: dict, actual: dict, delta=1):
        for address, balances in expected.items():
            self.assertIn(address, actual, msg=f'{address} is missing')
            self.assertAlmostEqual(balances['staking_balance'], actual[address]['staking_balance'], delta=delta, msg=address)

    @parameterized.expand([
        ('tz1ZRWFLgT9sz8iFi1VYWPfRYeUvUSFAaDao', 201),
        ('tz1Lhf4J9Qxoe3DZ2nfe8FGDnvVj7oKjnMY6', 185),  # double baking (loss)
        ('tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8', 74),   # double baking (gain)
        ('tz1PeZx7FXy7QRuMREGXGxeipb24RsMMzUNe', 135),  # double endorsement (loss)
        ('tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA', 135),  # double endorsement (gain)
        ('tz1S1Aew75hMrPUymqenKfHo8FspppXKpW7h', 233),  # revelation rewards
        ('tz1UUgPwikRHW1mEyVZfGYy6QaxrY6Y7WaG5', 207),  # revelation miss
    ])
    def test_get_rewards_for_cycle_map(self, address, cycle):
        rpc_rewards = load_reward_model(address, cycle, 'actual')
        if rpc_rewards is None:
            rpc_impl = RpcRewardApiImpl(
                nw=default_network_config_map['MAINNET'],
                baking_address=address,
                node_url='https://rpc.tzkt.io/mainnet')
            rpc_rewards = rpc_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)
            store_reward_model(address, cycle, 'actual', rpc_rewards)

        tzkt_impl = TzKTRewardApiImpl(
            nw=default_network_config_map['MAINNET'],
            baking_address=address)
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        self.assertAlmostEqual(rpc_rewards.delegate_staking_balance, tzkt_rewards.delegate_staking_balance, delta=1)
        self.assertAlmostEqual(rpc_rewards.total_reward_amount, tzkt_rewards.total_reward_amount, delta=1)
        self.assertBalancesAlmostEqual(rpc_rewards.delegator_balance_dict, tzkt_rewards.delegator_balance_dict, delta=1)

    @parameterized.expand([
        ('tz1YKh8T79LAtWxX29N5VedCSmaZGw9LNVxQ', 246),
        ('tz1ZRWFLgT9sz8iFi1VYWPfRYeUvUSFAaDao', 232),  # missed endorsements
        ('tz1S8e9GgdZG78XJRB3NqabfWeM37GnhZMWQ', 235),  # low-priority endorsements
        ('tz1RV1MBbZMR68tacosb7Mwj6LkbPSUS1er1', 242),  # missed blocks
        ('tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8', 233),  # stolen blocks
    ])
    def test_expected_rewards(self, address, cycle):
        tzstats_rewards = load_reward_model(address, cycle, 'expected')
        if tzstats_rewards is None:
            tzstats_impl = TzStatsRewardApiImpl(
                nw=default_network_config_map['MAINNET'],
                baking_address=address)
            tzstats_rewards = tzstats_impl.get_rewards_for_cycle_map(cycle, RewardsType.ESTIMATED)
            store_reward_model(address, cycle, 'expected', tzstats_rewards)

        tzkt_impl = TzKTRewardApiImpl(
            nw=default_network_config_map['MAINNET'],
            baking_address=address)
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ESTIMATED)

        self.assertAlmostEqual(
            tzstats_rewards.delegate_staking_balance, tzkt_rewards.delegate_staking_balance, delta=1)
        self.assertAlmostEqual(
            tzstats_rewards.total_reward_amount, tzkt_rewards.total_reward_amount, delta=1)
        self.assertBalancesAlmostEqual(
            tzstats_rewards.delegator_balance_dict, tzkt_rewards.delegator_balance_dict, delta=1)

    def test_staking_balance_issue(self):
        address = 'tz1V4qCyvPKZ5UeqdH14HN42rxvNPQfc9UZg'
        cycle = 220  # snapshot index == 15

        rpc_rewards = load_reward_model(address, cycle, 'actual')
        if rpc_rewards is None:
            rpc_impl = RpcRewardApiImpl(
                nw=default_network_config_map['MAINNET'],
                baking_address=address,
                node_url='https://rpc.tzkt.io/mainnet')
            rpc_rewards = rpc_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)
            store_reward_model(address, cycle, 'actual', rpc_rewards)

        tzkt_impl = TzKTRewardApiImpl(
            nw=default_network_config_map['MAINNET'],
            baking_address=address)
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        self.assertNotEqual(rpc_rewards.delegate_staking_balance, tzkt_rewards.delegate_staking_balance)
        self.assertAlmostEqual(rpc_rewards.total_reward_amount, tzkt_rewards.total_reward_amount, delta=1)

    def test_update_current_balances(self):
        log_items = [RewardLog(address='KT1Np1h72jGkRkfxNHLXNNJLHNbj9doPz4bR',
                               type='D',
                               staking_balance=100500,
                               current_balance=0)]
        tzkt_impl = TzKTRewardApiImpl(nw=default_network_config_map['MAINNET'],
                                      baking_address='tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA')
        tzkt_impl.update_current_balances(log_items)
        self.assertNotEqual(0, log_items[0].current_balance)
