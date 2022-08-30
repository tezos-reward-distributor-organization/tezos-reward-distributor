import logging
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from Constants import CURRENT_TESTNET, TZKT_PUBLIC_API_URL, PUBLIC_NODE_URL
from main import start_application
from tests.utils import Args, make_config


parsed_config = make_config(
    baking_address="tz1aWXP237BLwNHJcCD4b3DutCevhqq2T1Z9",
    payment_address="tz1aWXP237BLwNHJcCD4b3DutCevhqq2T1Z9",
    service_fee=0,
    min_delegation_amt=0,
    min_payment_amt=0,
)

# This overrides all logging within TRD to output everything during tests
sh = logging.StreamHandler()
sh.setFormatter(
    logging.Formatter("%(asctime)s - %(name)-9s - %(levelname)s - %(message)s")
)
test_logger = logging.getLogger("test")
test_logger.setLevel(logging.DEBUG)
test_logger.addHandler(sh)


@pytest.fixture
def args():
    # Test with PRPC node
    args = Args(
        initial_cycle=10,
        reward_data_provider="tzkt",
        api_base_url=TZKT_PUBLIC_API_URL[CURRENT_TESTNET],
    )
    args.network = CURRENT_TESTNET
    args.node_endpoint = PUBLIC_NODE_URL[CURRENT_TESTNET]
    args.docker = True
    args.dry_run = True
    args.dry_run_no_consumers = True
    args.syslog = False
    args.verbose = "off"
    args.do_not_publish_stats = True
    args.run_mode = 4
    return args


@patch("log_config.main_logger", test_logger)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigParser.load_file",
    MagicMock(return_value=parsed_config),
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_no_errors(args):
    assert start_application(args) == 0


@patch("log_config.main_logger", test_logger)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_load_file_error(args):
    assert start_application(args) == 0


@patch("log_config.main_logger", test_logger)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigParser.load_file", MagicMock(return_value="asasdasd")
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_illegal_baking_file(args):
    assert start_application(args) == 0


@patch("log_config.main_logger", test_logger)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigParser.load_file",
    MagicMock(return_value=parsed_config),
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_wrong_api_base_url(args):
    args.api_base_url = "https://api.carthage.tzkt.io_no_such_api/v1/"
    assert start_application(args) == 0


@patch("log_config.main_logger", test_logger)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigParser.load_file",
    MagicMock(return_value=parsed_config),
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_wrong_node_end_point(args):
    args.node_endpoint = "https://testnet-tezos.giganode.io:4433"
    assert start_application(args) == 0


@patch("log_config.main_logger", test_logger)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigParser.load_file",
    MagicMock(return_value=parsed_config),
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_wrong_reward_provider(args):
    args.reward_data_provider = "asdasdasd"
    assert start_application(args) == 0


@patch("util.process_life_cycle.verbose_logger", test_logger)
@patch("log_config.verbose_logger", test_logger)
@patch("log_config.init", MagicMock())
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch(
    "util.config_life_cycle.ConfigParser.load_file",
    MagicMock(return_value=parsed_config),
)
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
def test_wrong_args_run_mode(args):
    args.run_mode = 33
    assert start_application(args) == 0
