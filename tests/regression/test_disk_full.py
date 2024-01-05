import pytest
import queue
import logging
import vcr
from unittest.mock import MagicMock, patch
from src.pay.payment_producer import PaymentProducer
from src.pay.payment_consumer import PaymentConsumer
from tests.utils import Args, make_config
from src.plugins import plugins
from src.Constants import RunMode, TZKT_PUBLIC_API_URL, PUBLIC_NODE_URL
from src.cli.client_manager import ClientManager
from src.NetworkConfiguration import init_network_config
from src.model.baking_dirs import BakingDirs
from src.model.baking_conf import BakingConf
from src.api.provider_factory import ProviderFactory
from src.config.yaml_baking_conf_parser import BakingYamlConfParser
from src.calc.service_fee_calculator import ServiceFeeCalculator
from src.util.process_life_cycle import ProcessLifeCycle
from src.util.disk_is_full import disk_is_full

logger = logging.getLogger("unittesting")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

baking_config = make_config(
    baking_address="tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
    payment_address="tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
    service_fee=10,
    min_delegation_amt=0,
    min_payment_amt=0,
)


@pytest.fixture
def args():
    # Test with PRPC node
    args = Args(
        initial_cycle=10,
        reward_data_provider="tzkt",
        api_base_url=TZKT_PUBLIC_API_URL["MAINNET"],
    )
    args.network = "MAINNET"
    args.node_endpoint = PUBLIC_NODE_URL["MAINNET"]
    args.docker = True
    args.dry_run = True
    args.syslog = False
    args.verbose = "off"
    args.do_not_publish_stats = True
    args.run_mode = 3
    return args


@patch("src.log_config.main_logger", logger)
@patch(
    "src.util.disk_is_full.shutil.disk_usage", MagicMock(return_value=(10e9, 9e9, 5e8))
)
@vcr.use_cassette(
    "tests/regression/cassettes/test_disk_full_payment_producer.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_disk_full_payment_producer(args, caplog):
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
    assert disk_is_full()

    try:
        pp.daemon = True
        pp.start()

    finally:
        pp.stop()

    assert (
        "Disk is becoming full. Only 0.50 Gb left from 10.00 Gb. Please clean up disk to continue saving logs and reports."
        in caplog.text
    )


@patch("src.log_config.main_logger", logger)
@patch(
    "src.util.disk_is_full.shutil.disk_usage", MagicMock(return_value=(11e9, 8e9, 3e8))
)
@vcr.use_cassette(
    "tests/regression/cassettes/test_disk_full_payment_consumer.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_disk_full_payment_consumer(args, caplog):
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
    payments_queue = queue.Queue(50)
    plugins_manager = plugins.PluginManager(baking_cfg.get_plugins_conf(), args.dry_run)
    pc = PaymentConsumer(
        name="consumer0",
        payments_dir=baking_dirs.payments_root,
        key_name=baking_cfg.get_payment_address(),
        payments_queue=payments_queue,
        node_addr=args.node_endpoint,
        client_manager=client_manager,
        plugins_manager=plugins_manager,
        rewards_type=baking_cfg.get_rewards_type(),
        args=args,
        dry_run=args.dry_run,
        reactivate_zeroed=baking_cfg.get_reactivate_zeroed(),
        delegator_pays_ra_fee=baking_cfg.get_delegator_pays_ra_fee(),
        delegator_pays_xfer_fee=baking_cfg.get_delegator_pays_xfer_fee(),
        dest_map=baking_cfg.get_dest_map(),
        network_config=network_config_map[args.network],
        publish_stats=not args.do_not_publish_stats,
    )

    assert disk_is_full()

    try:
        pc.daemon = True
        pc.start()

    finally:
        pc.stop()

    assert (
        "Disk is becoming full. Only 0.30 Gb left from 11.00 Gb. Please clean up disk to continue saving logs and reports."
        in caplog.text
    )
