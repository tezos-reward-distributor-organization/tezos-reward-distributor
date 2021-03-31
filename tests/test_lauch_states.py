import logging
import unittest
from datetime import datetime
from os.path import join, dirname
from unittest.mock import MagicMock, patch

from main import start_application


class Args:
    def __init__(self, initial_cycle, reward_data_provider, node_addr_public=None, api_base_url=None):
        self.initial_cycle = initial_cycle
        self.run_mode = 3
        self.release_override = 0
        self.payment_offset = 0
        self.network = 'EDO2NET'
        self.node_endpoint = ''
        self.signer_endpoint = ''
        self.reward_data_provider = reward_data_provider
        self.node_addr_public = node_addr_public
        self.reports_base = join(dirname(__file__), reward_data_provider)
        self.config_dir = dirname(__file__)
        self.dry_run = True
        self.dry_run_no_consumers = True
        self.executable_dirs = dirname(__file__)
        self.docker = False
        self.background_service = False
        self.do_not_publish_stats = False
        self.retry_injected = False
        self.verbose = True
        self.api_base_url = api_base_url


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

    @patch('util.process_life_cycle.verbose_logger', test_logger)
    @patch('log_config.verbose_logger', test_logger)
    @patch('log_config.init', MagicMock())
    @patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
    @patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
    @patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
    @patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
    def test_wrong_args_run_mode(self):
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
        args.run_mode = 33

        start_application(args)
        pass
