import argparse
import json
import os
import queue
import sys
import time

import version
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
from launch_common import print_banner, add_argument_network, add_argument_provider, add_argument_reports_dir, \
    add_argument_config_dir, add_argument_node_addr, add_argument_dry, add_argument_dry_no_consumer, \
    add_argument_executable_dirs, add_argument_docker, add_argument_verbose
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
    logger.info("TRD version {} is running in {} mode.".format(version.version,"daemon" if args.background_service else "interactive"))
    logger.info("Arguments Configuration = {}".format( json.dumps(args.__dict__, indent=1)))

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
        logger.debug("Loading master configuration file {}".format(master_config_file_path))

        master_parser = YamlConfParser(ConfigParser.load_file(master_config_file_path))
        master_cfg = master_parser.parse()
    else:
        logger.debug("master configuration file not present.")

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
    dry_run = args.dry_run_no_consumers or args.dry_run
    if args.dry_run_no_consumers:
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
    life_cycle.start(not dry_run)

    # 9- service fee calculator
    srvc_fee_calc = ServiceFeeCalculator(cfg.get_full_supporters_set(), cfg.get_specials_map(), cfg.get_service_fee())

    if args.initial_cycle is None:
        recent = get_latest_report_file(payments_root)
        # if payment logs exists set initial cycle to following cycle
        # if payment logs does not exists, set initial cycle to 0, so that payment starts from last released rewards
        args.initial_cycle = 0 if recent is None else int(recent) + 1

        logger.info("initial_cycle set to {}".format(args.initial_cycle))

    p = PaymentProducer(name='producer', initial_payment_cycle=args.initial_cycle, network_config=network_config,
                        payments_dir=payments_root, calculations_dir=calculations_root, run_mode=RunMode(args.run_mode),
                        service_fee_calc=srvc_fee_calc, release_override=args.release_override,
                        payment_offset=args.payment_offset, baking_cfg=cfg, life_cycle=life_cycle,
                        payments_queue=payments_queue, dry_run=dry_run, wllt_clnt_mngr=wllt_clnt_mngr,
                        node_url=args.node_addr, provider_factory=provider_factory, verbose=args.verbose)
    p.start()

    publish_stats = not args.do_not_publish_stats
    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(name='consumer' + str(i), payments_dir=payments_root, key_name=payment_address,
                            client_path=client_path, payments_queue=payments_queue, node_addr=args.node_addr,
                            wllt_clnt_mngr=wllt_clnt_mngr, args=args, verbose=args.verbose, dry_run=dry_run,
                            delegator_pays_xfer_fee=cfg.get_delegator_pays_xfer_fee(), dest_map=cfg.get_dest_map(),
                            publish_stats=publish_stats)
        time.sleep(1)
        c.start()

        logger.info("Application start completed")
        logger.info(LINER)
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


def get_latest_report_file(payments_root):
    recent = None
    if get_successful_payments_dir(payments_root):
        files = sorted([os.path.splitext(x)[0] for x in os.listdir(get_successful_payments_dir(payments_root))],
                       key=lambda x: int(x))
        recent = files[-1] if len(files) > 0 else None
    return recent


class ReleaseOverrideAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not -11 <= values:
            parser.error("Valid range for release-override({0}) is [-11,) ".format(option_string))

        setattr(namespace, "release_override", values)


if __name__ == '__main__':

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    parser = argparse.ArgumentParser()

    add_argument_network(parser)
    add_argument_provider(parser)
    add_argument_reports_dir(parser)
    add_argument_config_dir(parser)
    add_argument_node_addr(parser)
    add_argument_dry(parser)
    add_argument_dry_no_consumer(parser)
    add_argument_executable_dirs(parser)
    add_argument_docker(parser)
    add_argument_verbose(parser)

    parser.add_argument("-s", "--background_service",
                        help="Marker to indicate that TRD is running in daemon mode. "
                             "When not given it indicates that TRD is in interactive mode.",
                        action="store_true")
    parser.add_argument("-Dp", "--do_not_publish_stats",
                        help="Do not publish anonymous usage statistics",
                        action="store_true")
    parser.add_argument("-M", "--run_mode",
                        help="Waiting decision after making pending payments. 1: default option. Run forever. "
                             "2: Run all pending payments and exit. 3: Run for one cycle and exit. "
                             "Suitable to use with -C option.",
                        default=1, choices=[1, 2, 3], type=int)
    parser.add_argument("-R", "--release_override",
                        help="Override NB_FREEZE_CYCLE value. last released payment cycle will be "
                             "(current_cycle-(NB_FREEZE_CYCLE+1)-release_override). Suitable for future payments. "
                             "For future payments give negative values. Valid range is [-11,)",
                        default=0, type=int, action=ReleaseOverrideAction)
    parser.add_argument("-O", "--payment_offset",
                        help="Number of blocks to wait after a cycle starts before starting payments. "
                             "This can be useful because cycle beginnings may be bussy.",
                        default=0, type=int)
    parser.add_argument("-C", "--initial_cycle",
                        help="First cycle to start payment. For last released rewards, set to 0. Non-positive values "
                             "are interpreted as: current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1). "
                             "If not set application will continue from last payment made or last reward released.",
                        type=int)

    args = parser.parse_args()
    script_name = ""
    print_banner(args, script_name)

    main(args)
