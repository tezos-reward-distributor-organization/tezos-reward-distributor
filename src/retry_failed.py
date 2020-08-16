import argparse
import json
import os
import queue
import sys
import time
from time import sleep

from Constants import RunMode, VERSION
from NetworkConfiguration import init_network_config
from api.provider_factory import ProviderFactory
from calc.service_fee_calculator import ServiceFeeCalculator
from cli.simple_client_manager import SimpleClientManager
from cli.wallet_client_manager import WalletClientManager
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from config.yaml_conf_parser import YamlConfParser
from log_config import main_logger
from main import LINER
from launch_common import add_argument_network, add_argument_reports_base, add_argument_provider, add_argument_config_dir, \
    add_argument_node_addr, add_argument_dry, add_argument_dry_no_consumer, add_argument_executable_dirs, \
    add_argument_docker, add_argument_verbose, print_banner
from model.baking_conf import BakingConf
from pay.payment_consumer import PaymentConsumer
from pay.payment_producer import PaymentProducer
from util.client_utils import get_client_path
from util.dir_utils import get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir
from util.process_life_cycle import ProcessLifeCycle
from storage.storage import Storage

nb_consumers = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger

life_cycle = ProcessLifeCycle()


def main(args):
    logger.info("TRD v{} - Retry Failed Helper".format(VERSION))
    logger.info("Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1)))

    # 1- find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 2- Load master configuration file if it is present
    master_config_file_path = os.path.join(config_dir, "master.yaml")

    master_cfg = {}
    if os.path.isfile(master_config_file_path):
        logger.info("Loading master configuration file {}".format(master_config_file_path))
        master_parser = YamlConfParser(ConfigParser.load_file(master_config_file_path))
        master_cfg = master_parser.parse()
    else:
        logger.info("master configuration file not present.")

    managers = None
    contracts_by_alias = None
    addresses_by_pkh = None

    if 'managers' in master_cfg:
        managers = master_cfg['managers']
    if 'contracts_by_alias' in master_cfg:
        contracts_by_alias = master_cfg['contracts_by_alias']
    if 'addresses_by_pkh' in master_cfg:
        addresses_by_pkh = master_cfg['addresses_by_pkh']

    # 3- get client path
    client_path = get_client_path([x.strip() for x in args.executable_dirs.split(',')],
                                  args.docker, args.network, args.verbose)

    logger.debug("Tezos client path is {}".format(client_path))

    # 4. get network config
    config_client_manager = SimpleClientManager(client_path, args.node_addr)
    network_config_map = init_network_config(args.network, config_client_manager, args.node_addr)
    network_config = network_config_map[args.network]

    logger.debug("Network config {}".format(network_config))

    # 5- load baking configuration file
    wllt_clnt_mngr = WalletClientManager(client_path, args.node_addr, contracts_by_alias, addresses_by_pkh, managers,
                                         verbose=args.verbose)

    # Setup provider to fetch RPCs
    provider_factory = ProviderFactory(args.reward_data_provider, verbose=args.verbose)

    # 5- is it a reports run
    dry_run = args.dry_run_no_consumers or args.dry_run
    if args.dry_run_no_consumers:
        nb_consumers = 0

    # 6- load config from database
    try:

        block_api = provider_factory.newBlockApi(network_config, args.node_addr)
        
        storage = Storage(config_dir, dry_run)

        # Get config from DB
        db_cfg_dict = ConfigStorage(storage).get_baker_config()
        db_cfg = BakingConf(db_cfg_dict, master_cfg)
        db_cfg.validate(wllt_clnt_mngr, block_api)
        db_cfg.process()

        baking_address = db_cfg.get_baking_address()
        payment_address = db_cfg.get_payment_address()

    except (ConfigStorageException, ConfigurationException) as e:
        logger.info("Unable to load/verify/convert '{}' config file.".format(config_file_path))
        logger.info(e)
        sys.exit(1)

    logger.info("Baking Configuration {}".format(db_cfg))

    logger.info(LINER)
    logger.info("BAKING ADDRESS is {}".format(baking_address))
    logger.info("PAYMENT ADDRESS is {}".format(payment_address))
    logger.info(LINER)

    # 7- get reporting directories
    reports_base = os.path.expanduser(args.reports_base)
    if dry_run:
        reports_base = os.path.expanduser("./reports")

    reports_dir = os.path.join(reports_base, baking_address)
    payments_root = get_payment_root(reports_dir, create=True)
    calculations_root = get_calculations_root(reports_dir, create=True)

    # 8- start the life cycle
    life_cycle.start(False)

    # 9- service fee calculator
    srvc_fee_calc = ServiceFeeCalculator(db_cfg.get_full_supporters_set(), db_cfg.get_specials_map(), db_cfg.get_service_fee())

    try:

        p = PaymentProducer(name='producer', initial_payment_cycle=None, network_config=network_config,
                            payments_dir=payments_root, calculations_dir=calculations_root, run_mode=RunMode.ONETIME,
                            service_fee_calc=srvc_fee_calc, release_override=0,
                            payment_offset=0, baking_cfg=db_cfg, life_cycle=life_cycle,
                            payments_queue=payments_queue, dry_run=dry_run, wllt_clnt_mngr=wllt_clnt_mngr,
                            node_url=args.node_addr, provider_factory=provider_factory, storage=storage,
                            node_url_public=args.node_addr_public, verbose=args.verbose)

        p.retry_failed_payments(args.retry_injected)

        c = PaymentConsumer(name='consumer_retry_failed', payments_dir=payments_root, storage=storage, key_name=payment_address,
                            client_path=client_path, payments_queue=payments_queue, node_addr=args.node_addr,
                            wllt_clnt_mngr=wllt_clnt_mngr, verbose=args.verbose, dry_run=dry_run,
                            reactivate_zeroed=db_cfg.get_reactivate_zeroed(),
                            delegator_pays_ra_fee=db_cfg.get_delegator_pays_ra_fee(),
                            delegator_pays_xfer_fee=db_cfg.get_delegator_pays_xfer_fee(), dest_map=db_cfg.get_dest_map(),
                            network_config=network_config, publish_stats=not args.do_not_publish_stats)
        time.sleep(1)
        c.start()
        p.exit()
        c.join()

        logger.info("Application start completed")
        logger.info(LINER)

        sleep(5)

    except KeyboardInterrupt:
        logger.info("Interrupted.")


if __name__ == '__main__':

    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception("Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major,sys.version_info.minor ))

    parser = argparse.ArgumentParser()
    add_argument_network(parser)
    add_argument_provider(parser)
    add_argument_reports_base(parser)
    add_argument_config_dir(parser)
    add_argument_node_addr(parser)
    add_argument_dry(parser)
    add_argument_dry_no_consumer(parser)
    add_argument_executable_dirs(parser)
    add_argument_docker(parser)
    add_argument_verbose(parser)

    parser.add_argument("-inj", "--retry_injected", help="Try to pay injected payment items. Use this option only if you are sure that payment items were injected but not actually paid.", action="store_true")
    args = parser.parse_args()
    script_name = " - Retry Failed Files"
    print_banner(args, script_name)

    main(args)
