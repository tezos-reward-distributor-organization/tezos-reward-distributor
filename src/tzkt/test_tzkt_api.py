import unittest
import pandas as pd
from unittest.mock import patch, MagicMock
from os.path import dirname, join
from decimal import Decimal
from parameterized import parameterized

from main import main
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzkt.tzkt_block_api import TzKTBlockApiImpl
from tzkt.tzkt_reward_api import TzKTRewardApiImpl, RewardLog
from NetworkConfiguration import default_network_config_map


dummy_addr_dict = dict(
    pkh='pkh',
    originated=False,
    alias='alias',
    sk='secret_key',
    manager='manager',
    revealed=True
)


class Args:

    def __init__(self, initial_cycle, reward_data_provider):
        self.initial_cycle = initial_cycle
        self.run_mode = 3
        self.release_override = 0
        self.payment_offset = 0
        self.network = 'MAINNET'
        self.node_addr = 'mainnet-tezos.giganode.io:443'
        self.reward_data_provider = reward_data_provider
        self.node_addr_public = ''
        self.reports_base = join(dirname(__file__), reward_data_provider)
        self.config_dir = dirname(__file__)
        self.dry_run = True
        self.dry_run_no_consumers = True
        self.executable_dirs = dirname(__file__)
        self.docker = True
        self.background_service = False
        self.do_not_publish_stats = False
        self.verbose = True


def make_config(baking_address, payment_address, service_fee: int,
                min_delegation_amt: int, delegator_pays_xfer_fee: bool) -> str:
    return f'version: 1.0\n' \
           f'baking_address: {baking_address}\n' \
           f'payment_address: {payment_address}\n' \
           f'service_fee: {service_fee}\n' \
           f'founders_map: {{}}\n' \
           f'owners_map: {{}}\n' \
           f'specials_map: {{}}\n' \
           f'supporters_set: {{}}\n' \
           f'min_delegation_amt: {min_delegation_amt}\n' \
           f'reactivate_zeroed: True\n' \
           f'delegator_pays_xfer_fee: {delegator_pays_xfer_fee}\n' \
           f'delegator_pays_ra_fee: False\n' \
           f'rules_map:\n  mindelegation: TOB'


def parse_report_rewards(baking_address, initial_cycle) -> dict:
    report_file = join(dirname(__file__), f'reports/{baking_address}/calculations/{initial_cycle}.csv')
    df = pd.read_csv(report_file)
    df.set_index('address', inplace=True)
    df = df[(df['type'] == 'D') & (df['skipped'] == 0)]
    df['amount'] = df['amount'].apply(lambda x: Decimal(x / 10 ** 6).quantize(Decimal('0.000001')))
    return df['amount'].to_dict()


@patch('pay.payment_producer.sleep', MagicMock())
@patch('pay.payment_producer.time', MagicMock(sleep=MagicMock()))
@patch('main.time', MagicMock(sleep=MagicMock()))
@patch('main.get_client_path', MagicMock())
@patch('main.get_baking_configuration_file', MagicMock(return_value=''))
@patch('main.ProcessLifeCycle', MagicMock(is_running=MagicMock(return_value=False)))
@patch('main.WalletClientManager', MagicMock(get_addr_dict_by_pkh=MagicMock(return_value=dummy_addr_dict)))
@patch('main.ConfigParser')
class IntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    def test_dry_run(self, ConfigParser):
        ConfigParser.load_file = MagicMock(return_value=make_config(
            baking_address='tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB',
            payment_address='tz1Zrqm4TkJwqTxm5TiyVFh6taXG4Wrq7tko',
            service_fee=9,
            min_delegation_amt=10,
            delegator_pays_xfer_fee=True
        ))
        main(Args(initial_cycle=201, reward_data_provider='tzkt'))
        # tzkt_rewards = parse_report_rewards(
        #     baking_address='tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB',
        #     initial_cycle=201)


@patch('rpc.rpc_reward_api.sleep', MagicMock())
@patch('rpc.rpc_reward_api.logger', MagicMock(debug=MagicMock(side_effect=print)))
class RewardApiImplTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None

    @parameterized.expand([
        ('tz1ZRWFLgT9sz8iFi1VYWPfRYeUvUSFAaDao', 201),
        ('tz1Lhf4J9Qxoe3DZ2nfe8FGDnvVj7oKjnMY6', 185),  # double baking (loss)
        ('tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8', 74),   # double baking (gain)
        ('tz1PeZx7FXy7QRuMREGXGxeipb24RsMMzUNe', 135),  # double endorsement (loss)
        ('tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA', 135),  # double endorsement (gain)
    ])
    def test_get_rewards_for_cycle_map(self, address, cycle):
        rpc_impl = RpcRewardApiImpl(
            nw=default_network_config_map['MAINNET'],
            baking_address=address,
            node_url='https://mainnet-tezos.giganode.io')
        tzkt_impl = TzKTRewardApiImpl(
            nw=default_network_config_map['MAINNET'],
            baking_address=address)
        rpc_rewards = rpc_impl.get_rewards_for_cycle_map(cycle)
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle)
        self.assertEqual(rpc_rewards.delegate_staking_balance, tzkt_rewards.delegate_staking_balance)
        self.assertEqual(rpc_rewards.total_reward_amount, tzkt_rewards.total_reward_amount)
        self.assertDictEqual(rpc_rewards.delegator_balance_dict, tzkt_rewards.delegator_balance_dict)

    def test_update_current_balances(self):
        log_items = [RewardLog(address='KT1Np1h72jGkRkfxNHLXNNJLHNbj9doPz4bR',
                               type='D',
                               staking_balance=100500,
                               current_balance=0)]
        tzkt_impl = TzKTRewardApiImpl(nw=default_network_config_map['MAINNET'],
                                      baking_address='tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA')
        tzkt_impl.update_current_balances(log_items)
        self.assertNotEqual(0, log_items[0].current_balance)


class BlockApiImplTests(unittest.TestCase):

    def test_get_head(self):
        tzkt_impl = TzKTBlockApiImpl(nw=default_network_config_map['MAINNET'])
        level = tzkt_impl.get_current_level()
        self.assertNotEqual(0, level)


if __name__ == '__main__':
    unittest.main()
