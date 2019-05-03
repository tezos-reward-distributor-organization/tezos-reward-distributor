import argparse
import json
import os
import queue
import sys
import time
from time import sleep

from Constants import RunMode
from NetworkConfiguration import init_network_config
from api.provider_factory import ProviderFactory
from calc.service_fee_calculator import ServiceFeeCalculator
from cli.simple_client_manager import SimpleClientManager
from cli.wallet_client_manager import WalletClientManager
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from config.yaml_conf_parser import YamlConfParser
from log_config import main_logger
from model.baking_conf import BakingConf
from pay.payment_consumer import PaymentConsumer
from pay.payment_producer import PaymentProducer
from util.client_utils import get_client_path
from util.dir_utils import get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir
from util.process_life_cycle import ProcessLifeCycle

LINER = "--------------------------------------------"

NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger

life_cycle = ProcessLifeCycle()


def main(args):
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
                                  args.docker, args.network,
                                  args.verbose)

    logger.debug("Tezos client path is {}".format(client_path))

    # 4. get network config     
    config_client_manager = SimpleClientManager(client_path)
    network_config_map = init_network_config(args.network, config_client_manager, args.node_addr)
    network_config = network_config_map[args.network]

    # 5- load baking configuration file
    config_file_path = get_baking_configuration_file(config_dir)

    logger.info("Loading baking configuration file {}".format(config_file_path))

    wllt_clnt_mngr = WalletClientManager(client_path, contracts_by_alias, addresses_by_pkh, managers,
                                         verbose=args.verbose)

    provider_factory = ProviderFactory(args.reward_data_provider)
    parser = BakingYamlConfParser(ConfigParser.load_file(config_file_path), wllt_clnt_mngr, provider_factory,
                                  network_config, args.node_addr)
    parser.parse()
    parser.validate()
    parser.process()
    cfg_dict = parser.get_conf_obj()

    # dictionary to BakingConf object, for a bit of type safety
    cfg = BakingConf(cfg_dict, master_cfg)

    logger.info("Baking Configuration {}".format(cfg))

    baking_address = cfg.get_baking_address()
    payment_address = cfg.get_payment_address()
    logger.info(LINER)
    logger.info("BAKING ADDRESS is {}".format(baking_address))
    logger.info("PAYMENT ADDRESS is {}".format(payment_address))
    logger.info(LINER)

    # 6- is it a reports run
    dry_run = args.dry_run_no_payments or args.dry_run
    if args.dry_run_no_payments:
        global NB_CONSUMERS
        NB_CONSUMERS = 0

    # 7- get reporting directories
    reports_dir = os.path.expanduser(args.reports_dir)
    # if in reports run mode, do not create consumers
    # create reports in reports directory
    if dry_run:
        reports_dir = os.path.expanduser("./reports")

    reports_dir = os.path.join(reports_dir, baking_address)

    payments_root = get_payment_root(reports_dir, create=True)
    calculations_root = get_calculations_root(reports_dir, create=True)
    get_successful_payments_dir(payments_root, create=True)
    get_failed_payments_dir(payments_root, create=True)

    # 8- start the life cycle
    life_cycle.start(False)

    # 9- service fee calculator
    srvc_fee_calc = ServiceFeeCalculator(cfg.get_full_supporters_set(), cfg.get_specials_map(), cfg.get_service_fee())

    p = PaymentProducer(name='producer', initial_payment_cycle=None, network_config=network_config,
                        payments_dir=payments_root, calculations_dir=calculations_root, run_mode=RunMode.ONETIME,
                        service_fee_calc=srvc_fee_calc, release_override=0,
                        payment_offset=0, baking_cfg=cfg, life_cycle=life_cycle,
                        payments_queue=payments_queue, dry_run=dry_run, wllt_clnt_mngr=wllt_clnt_mngr,
                        node_url=args.node_addr, provider_factory=provider_factory, verbose=args.verbose)
    p.retry_failed_payments()

    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(name='consumer' + str(i), payments_dir=payments_root, key_name=payment_address,
                            client_path=client_path, payments_queue=payments_queue, node_addr=args.node_addr,
                            wllt_clnt_mngr=wllt_clnt_mngr, verbose=args.verbose, dry_run=dry_run,
                            delegator_pays_xfer_fee=cfg.get_delegator_pays_xfer_fee())
        time.sleep(1)
        c.start()

        logger.info("Application start completed")
        logger.info(LINER)

    sleep(5)
    p.exit()
    try:
        while life_cycle.is_running(): time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        life_cycle.stop()


def get_baking_configuration_file(config_dir):
    config_file = None
    for file in os.listdir(config_dir):
        if file.endswith(".yaml") and not file.startswith("master"):
            if config_file:
                raise Exception(
                    "Application only supports one baking configuration file. Found at least 2 {}, {}".format(
                        config_file, file))
            config_file = file
    if config_file is None:
        raise Exception(
            "Unable to find any '.yaml' configuration files inside configuration directory({})".format(config_dir))

    return os.path.join(config_dir, config_file)



if __name__ == '__main__':

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    parser = argparse.ArgumentParser()
    parser.add_argument("-N", "--network", help="network name", choices=['ZERONET', 'ALPHANET', 'MAINNET'],
                        default='MAINNET')
    parser.add_argument("-P", "--reward_data_provider", help="where reward data is provided", choices=['tzscan', 'rpc'],
                        default='tzscan')
    parser.add_argument("-r", "--reports_dir", help="Directory to create reports", default='~/pymnt/reports')
    parser.add_argument("-f", "--config_dir", help="Directory to find baking configurations", default='~/pymnt/cfg')
    parser.add_argument("-A", "--node_addr", help="Node host:port pair", default='127.0.0.1:8732')
    parser.add_argument("-D", "--dry_run",
                        help="Run without injecting payments. Suitable for testing. Does not require locking.",
                        action="store_true")
    parser.add_argument("-Dn", "--dry_run_no_payments",
                        help="Run without doing any payments. Suitable for testing. Does not require locking.",
                        action="store_true")
    parser.add_argument("-E", "--executable_dirs",
                        help="Comma separated list of directories to search for client executable. Prefer single "
                             "location when setting client directory. If -d is set, point to location where tezos docker "
                             "script (e.g. mainnet.sh for mainnet) is found. Default value is given for minimum configuration effort.",
                        default='~/,~/tezos')
    parser.add_argument("-d", "--docker",
                        help="Docker installation flag. When set, docker script location should be set in -E",
                        action="store_true")
    parser.add_argument("-V", "--verbose",
                        help="Low level details.",
                        action="store_true")

    args = parser.parse_args()

    logger.info("Tezos Reward Distributor - Retry Failed Files is Starting")
    logger.info(LINER)
    logger.info("Copyright Huseyin ABANOZ 2019")
    logger.info("huseyinabanox@gmail.com")
    logger.info("Please leave copyright information")
    logger.info(LINER)
    if args.dry_run:
        logger.info("DRY RUN MODE")
        logger.info(LINER)
    main(args)
