import pytest
import queue
import logging
from unittest.mock import patch
from pay.payment_producer import PaymentProducer
from tests.utils import Args, make_config
from Constants import RunMode
from cli.client_manager import ClientManager
from NetworkConfiguration import init_network_config
from model.baking_dirs import BakingDirs
from model.baking_conf import BakingConf
from api.provider_factory import ProviderFactory
from config.yaml_baking_conf_parser import BakingYamlConfParser
from calc.service_fee_calculator import ServiceFeeCalculator
from util.process_life_cycle import ProcessLifeCycle

logger = logging.getLogger("unittesting")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

baking_config = make_config(
    "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
    "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
    10,
    0,
)


@pytest.fixture
def args():
    # Test with PRPC node
    args = Args(
        initial_cycle=10,
        reward_data_provider="tzkt",
        api_base_url="https://api.tzkt.io/v1/",
    )
    args.network = "MAINNET"
    args.node_endpoint = "https://testnet-tezos.giganode.io"
    args.docker = True
    args.dry_run = True
    args.dry_run_no_consumers = True
    args.syslog = False
    args.verbose = "off"
    args.log_file = "logs/app.log"
    args.do_not_publish_stats = True
    args.run_mode = 3
    return args


@patch("log_config.main_logger", logger)
def test_disk_full(args, caplog):
    # Issue: https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/504
    client_manager = ClientManager(args.node_endpoint, args.signer_endpoint)
    network_config_map = init_network_config(args.network, client_manager)
    factory = ProviderFactory(provider="prpc")
    parser = BakingYamlConfParser(
        baking_config, None, None, None, None, block_api=factory, api_base_url=None
    )
    parser.parse()
    parser.process()

    cfg_dict = parser.get_conf_obj()
    baking_cfg = BakingConf(cfg_dict)
    baking_dirs = BakingDirs(args, baking_cfg.get_baking_address())
    srvc_fee_calc = ServiceFeeCalculator(
        baking_cfg.get_full_supporters_set(),
        baking_cfg.get_specials_map(),
        baking_cfg.get_service_fee(),
    )
    payments_queue = queue.Queue(50)
    plc = ProcessLifeCycle(None)
    pp = PaymentProducer(
        name="producer",
        network_config=network_config_map[args.network],
        payments_dir=baking_dirs.payments_root,
        calculations_dir=baking_dirs.calculations_root,
        run_mode=RunMode(args.run_mode),
        service_fee_calc=srvc_fee_calc,
        release_override=args.release_override,
        payment_offset=args.payment_offset,
        baking_cfg=baking_cfg,
        life_cycle=plc,
        payments_queue=payments_queue,
        dry_run=args.dry_run,
        client_manager=client_manager,
        node_url=args.node_endpoint,
        reward_data_provider=args.reward_data_provider,
        node_url_public=args.node_addr_public,
        api_base_url=args.api_base_url,
        retry_injected=args.retry_injected,
        initial_payment_cycle=args.initial_cycle,
    )
    pp.disk_usage = lambda: (10e9, 9e9, 1e9)
    assert not pp.disk_is_full()

    pp.disk_usage = lambda: (10e9, 9e9, 5e8)
    assert pp.disk_is_full()
    pp.daemon = True
    pp.start()
    assert (
        "Disk is becoming full. Only 0.50 Gb left from 10.00 Gb. Please clean up disk to continue saving logs and reports."
        in caplog.text
    )
