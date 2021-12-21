import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from main import start_application
from tests.utils import Args, make_config
from Constants import TZKT_PUBLIC_API_URL, PUBLIC_NODE_URL


@pytest.fixture
def args():
    # Test with PRPC node
    args = Args(
        initial_cycle=201,
        reward_data_provider="tzkt",
        api_base_url=TZKT_PUBLIC_API_URL["MAINNET"],
    )
    args.network = "MAINNET"
    args.node_endpoint = PUBLIC_NODE_URL["MAINNET"]
    args.docker = True
    args.dry_run = True
    args.dry_run_no_consumers = True
    args.syslog = False
    args.verbose = "on"
    args.log_file = "logs/app.log"
    args.do_not_publish_stats = True
    args.run_mode = 3
    return args


@patch("pay.payment_producer.sleep", MagicMock())
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch("util.config_life_cycle.ConfigParser")
def test_dry_run(ConfigParser, args):
    ConfigParser.load_file = MagicMock(
        return_value=make_config(
            baking_address="tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB",
            payment_address="tz1Zrqm4TkJwqTxm5TiyVFh6taXG4Wrq7tko",
            service_fee=9,
            min_delegation_amt=10,
        )
    )
    assert start_application(args) == 0


@patch("pay.payment_producer.sleep", MagicMock())
@patch(
    "util.config_life_cycle.ConfigLifeCycle.get_baking_cfg_file",
    MagicMock(return_value=""),
)
@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
@patch(
    "cli.client_manager.ClientManager.get_bootstrapped",
    MagicMock(return_value=datetime(2030, 1, 1)),
)
@patch("util.config_life_cycle.ConfigParser")
def test_base_url(ConfigParser, args):
    ConfigParser.load_file = MagicMock(
        return_value=make_config(
            baking_address="tz1aWXP237BLwNHJcCD4b3DutCevhqq2T1Z9",
            payment_address="tz1aWXP237BLwNHJcCD4b3DutCevhqq2T1Z9",
            service_fee=0,
            min_delegation_amt=0,
        )
    )
    args.initial_cycle = 100
    args.api_base_url = TZKT_PUBLIC_API_URL["MAINNET"]
    assert start_application(args) == 0
