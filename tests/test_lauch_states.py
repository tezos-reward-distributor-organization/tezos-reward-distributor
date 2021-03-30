import argparse
import logging
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from main import start_application
from test_tzkt_api import Args


def illegal_run_mode():
    parser = argparse.ArgumentParser()
    parser.add_argument('--initial_cycle', default=10)
    parser.add_argument('--reward_data_provider', default='tzkt')
    parser.add_argument('--api_base_url', default='https://api.carthage.tzkt.io/v1/')
    parser.add_argument('--node_endpoint', default='https://testnet-tezos.giganode.io:443')
    parser.add_argument('--docker', default=True)
    parser.add_argument('--dry_run', default=True)
    parser.add_argument('--dry_run_no_consumers', default=True)
    parser.add_argument('--syslog', default=False)
    parser.add_argument('--verbose', default='on')
    parser.add_argument('--log_file', default='logs/app.log')
    parser.add_argument('--do_not_publish_stats', default='True')
    parser.add_argument('--run_mode', default=33)
    parser.add_argument('--network', default='MAINNET')
    parser.add_argument('--payment_offset', default=0)
    parser.add_argument('--release_override', default=0)
    parser.add_argument('--background_service', default=False)
    parser.add_argument('--signer_endpoint', default='http://127.0.0.1:6732')
    parser.add_argument('--config_dir', default='~/pymnt/cfg')
    parser.add_argument('--reports_base', default='~/pymnt/reports')
    parser.add_argument('--node_addr_public', default='')
    parser.add_argument('--retry_injected', default=False)

    return parser


def make_config(baking_address, payment_address, service_fee: int,
                min_delegation_amt: int) -> str:
    return \
        "baking_address: {:s}\n" \
        "delegator_pays_ra_fee: true\n" \
        "delegator_pays_xfer_fee: true\n" \
        "founders_map:\n" \
        "  tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7: 0.25\n" \
        "  tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace: 0.75\n" \
        "min_delegation_amt: {:d}\n" \
        "owners_map:\n" \
        "  tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk: 1.0\n" \
        "payment_address: {:s}\n" \
        "reactivate_zeroed: true\n" \
        "rules_map:\n" \
        "  tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs\n" \
        "  tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT: TOB\n" \
        "  mindelegation: TOB\n" \
        "service_fee: {:d}\n" \
        "specials_map: {{}}\n" \
        "supporters_set: !!set {{}}\n" \
        "plugins:\n" \
        "  enabled:\n".format(
            baking_address, min_delegation_amt, payment_address, service_fee)


class TestLaunchStates(unittest.TestCase):
    parsed_config = make_config(
        baking_address='tz1aWXP237BLwNHJcCD4b3DutCevhqq2T1Z9',
        payment_address='tz1aWXP237BLwNHJcCD4b3DutCevhqq2T1Z9',
        service_fee=0,
        min_delegation_amt=0
    )

    # This overrides all logging within TRD to output everything during tests
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter('%(asctime)s - %(name)-9s - %(message)s'))
    test_logger = logging.getLogger('test')
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(sh)

    @patch('log_config.main_logger', test_logger)
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_no_errors(self):

        # Test with PRPC node
        args = Args(initial_cycle=10, reward_data_provider='tzkt', api_base_url='https://api.carthage.tzkt.io/v1/')
        args.node_endpoint = 'https://testnet-tezos.giganode.io:443'
        args.docker = True
        args.dry_run = True
        args.dry_run_no_consumers = True
        args.syslog = False
        args.verbose = "off"
        args.log_file = 'logs/app.log'
        args.do_not_publish_stats = True
        args.run_mode = 4

        start_application(args)

    @patch('log_config.main_logger', test_logger)
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=None))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_load_file_error(self):
        # Test with PRPC node
        args = Args(initial_cycle=10, reward_data_provider='tzkt', api_base_url='https://api.carthage.tzkt.io/v1/')
        args.node_endpoint = 'https://testnet-tezos.giganode.io:443'
        args.docker = True
        args.dry_run = True
        args.dry_run_no_consumers = True
        args.syslog = False
        args.verbose = "off"
        args.log_file = 'logs/app.log'
        args.do_not_publish_stats = True
        args.run_mode = 4

        start_application(args)

    @patch('log_config.main_logger', test_logger)
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_wrong_api_base_url(self):
        # Test with PRPC node
        args = Args(initial_cycle=10, reward_data_provider='tzkt', api_base_url='https://api.carthage.tzkt.io_no_such_api/v1/')
        args.node_endpoint = 'https://testnet-tezos.giganode.io:443'
        args.docker = True
        args.dry_run = True
        args.dry_run_no_consumers = True
        args.syslog = False
        args.verbose = "off"
        args.log_file = 'logs/app.log'
        args.do_not_publish_stats = True
        args.run_mode = 3

        start_application(args)

    @patch('log_config.main_logger', test_logger)
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_wrong_node_end_point(self):
        # Test with PRPC node
        args = Args(initial_cycle=10, reward_data_provider='tzkt', api_base_url='https://api.carthage.tzkt.io/v1/')
        args.node_endpoint = 'https://testnet-tezos.giganode.io:4433'
        args.docker = True
        args.dry_run = True
        args.dry_run_no_consumers = True
        args.syslog = False
        args.verbose = "off"
        args.log_file = 'logs/app.log'
        args.do_not_publish_stats = True
        args.run_mode = 3

        start_application(args)

    @patch('log_config.main_logger', test_logger)
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_wrong_reward_provider(self):
        # Test with PRPC node
        args = Args(initial_cycle=10, reward_data_provider='tzkt33', api_base_url='https://api.carthage.tzkt.io/v1/')
        args.node_endpoint = 'https://testnet-tezos.giganode.io:443'
        args.docker = True
        args.dry_run = True
        args.dry_run_no_consumers = True
        args.syslog = False
        args.verbose = "off"
        args.log_file = 'logs/app.log'
        args.do_not_publish_stats = True
        args.run_mode = 3

        start_application(args)
        pass

    @patch('launch_common.build_parser', MagicMock(return_value=illegal_run_mode()))
    @patch('util.process_life_cycle.verbose_logger', test_logger)
    @patch('log_config.verbose_logger', test_logger)
    @patch('log_config.init', MagicMock())
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_wrong_args_run_mode(self):
        start_application(None)
        pass


