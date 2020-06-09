import unittest
import requests
import pandas as pd
import simplejson as json
from unittest.mock import patch
from os.path import dirname, join
from decimal import Decimal

from main import main


class Args:

    def __init__(self, **kwargs):
        self.initial_cycle = kwargs.get('initial_cycle', 0)
        self.run_mode = 3
        self.release_override = 0
        self.payment_offset = 0
        self.network = 'MAINNET'
        self.node_addr = 'mainnet-tezos.giganode.io'
        self.reward_data_provider = 'tzkt'
        self.node_addr_public = ''
        self.reports_base = dirname(__file__)
        self.config_dir = dirname(__file__)
        self.dry_run = True
        self.dry_run_no_consumers = True
        self.executable_dirs = dirname(__file__)
        self.docker = True
        self.background_service = False
        self.do_not_publish_stats = False
        self.verbose = True


def get_bb_rewards(baker_address, cycle) -> dict:
    res = requests.get(f'https://api.baking-bad.org/v1/rewards/{baker_address}?cycle={cycle}')
    data = json.loads(res.text, use_decimal=True)
    return {
        item['address']: item['amount']
        for item in data['payouts']
    }


def parse_report_rewards(report_file, baker_address, cycle) -> dict:
    df = pd.read_csv(report_file)
    df.set_index('address', inplace=True)
    df = df[(df['type'] == 'D') & (df['skipped'] == 0)]
    df['amount'] = df['amount'].apply(lambda x: Decimal(x / 10 ** 6).quantize(Decimal('0.000001')))
    return df['amount'].to_dict()


class ValidatePayouts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.maxDiff = None
        cls.cycle = 200
        cls.baker_address = 'tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB'

    @patch('pay.payment_producer.sleep')
    @patch('main.get_client_path')
    @patch('main.WalletClientManager')
    @patch('main.ProcessLifeCycle')
    def test_generate_report(self, ProcessLifeCycle, WalletClientManager, _get_client_path, _sleep):
        WalletClientManager.get_addr_dict_by_pkh = dict(
            pkh=self.baker_address,
            originated=False,
            alias='alias',
            sk='secret_key',
            manager=self.baker_address,
            revealed=True
        )
        ProcessLifeCycle.is_running.return_value = False
        main(Args(initial_cycle=self.cycle))

    def test_validate_report(self):
        actual_rewards = parse_report_rewards(
            report_file=join(dirname(__file__), f'reports/{self.baker_address}/calculations/{self.cycle}.csv'),
            baker_address=self.baker_address,
            cycle=self.cycle
        )
        expected_rewards = get_bb_rewards(self.baker_address, self.cycle)
        self.assertDictEqual(expected_rewards, actual_rewards)


if __name__ == '__main__':
    unittest.main()
