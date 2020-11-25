import logging
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from os.path import dirname, join

from main import main  # This imports main() from src/main.py


# This is a dummy class representing any --arguments passed on the command line
# You can instantiate this class and then change any parameters for testing
class Args:

    def __init__(self, initial_cycle, reward_data_provider, node_addr_public=None, api_base_url=None):
        self.initial_cycle = initial_cycle
        self.run_mode = 3
        self.release_override = 0
        self.payment_offset = 0
        self.network = 'ALPHANET'
        self.node_addr = ''
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


# This helper function creates a YAML bakers config
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


# Create a config object that can be injected to simulate loading a yaml config file
parsed_config = make_config(
    baking_address='tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V',
    payment_address='tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs',
    service_fee=10,
    min_delegation_amt=0
)

# This is a dummy address dictionary normally used by wallet manager
dummy_addr_dict = dict(
    pkh='pkh',
    originated=False,
    alias='alias',
    sk='secret_key',
    manager='manager',
    revealed=True
)

# This overrides all logging within TRD to output everything during tests
sh = logging.StreamHandler()
sh.setFormatter(logging.Formatter('%(asctime)s - %(name)-9s - %(message)s'))
test_logger = logging.getLogger('main')
test_logger.setLevel(logging.DEBUG)
test_logger.addHandler(sh)


@patch('main.get_baking_configuration_file', MagicMock(return_value=''))
@patch('main.get_client_path', MagicMock(return_value='/bin/false'))
@patch('main.ProcessLifeCycle', MagicMock(is_running=MagicMock(return_value=False)))
@patch('log_config.main_logger', test_logger)
@patch.multiple('main.WalletClientManager',
                get_addr_dict_by_pkh=MagicMock(return_value=dummy_addr_dict),
                get_bootstrapped=MagicMock(return_value=datetime(2030, 1, 1)))
@patch('main.ConfigParser.load_file', MagicMock(return_value=parsed_config))
class RpcApiTest(unittest.TestCase):

    def test_dry_run(self):

        # Test with PRPC node
        args = Args(initial_cycle=90, reward_data_provider='prpc', node_addr_public='https://delphinet-tezos.giganode.io')
        args.node_addr = 'https://delphinet-tezos.giganode.io:443'
        args.docker = True
        main(args)
