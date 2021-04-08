import pytest
import logging
from datetime import datetime
from unittest.mock import patch, MagicMock
from tests.utils import Args, make_config
from Constants import CURRENT_TESTNET
from main import start_application


@pytest.fixture
def args():
    args = Args(initial_cycle=90, reward_data_provider='prpc', node_addr_public='https://testnet-tezos.giganode.io')
    args.network = CURRENT_TESTNET
    args.node_endpoint = 'https://testnet-tezos.giganode.io:443'
    args.docker = False
    args.dry_run = True
    args.dry_run_no_consumers = True
    args.syslog = False
    args.log_file = 'logs/app.log'
    args.do_not_publish_stats = True
    args.run_mode = 4  # retry fail
    return args


# Create a config object that can be injected to simulate loading a yaml config file
parsed_config = make_config(
    baking_address='tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V',
    payment_address='tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs',
    service_fee=10,
    min_delegation_amt=0
)

# This overrides all logging within TRD to output everything during tests
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)-9s - %(levelname)s - %(message)s'))
test_logger = logging.getLogger('main')
test_logger.setLevel(logging.DEBUG)
test_logger.addHandler(sh)


@patch('log_config.main_logger', test_logger)
@patch('cli.client_manager.ClientManager.check_pkh_known_by_signer', MagicMock(return_value=True))
@patch('cli.client_manager.ClientManager.get_bootstrapped', MagicMock(return_value=datetime(2030, 1, 1)))
@patch('util.config_life_cycle.ConfigParser.load_file', MagicMock(return_value=parsed_config))
@patch('util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file', MagicMock(return_value=""))
def test_rpc_api_dry_run(args):
    assert start_application(args) == 0
