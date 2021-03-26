import json
import os
import queue
import sys
from time import sleep

from launch_common import print_banner, parse_arguments
from Constants import RunMode, VERSION
from NetworkConfiguration import init_network_config
from api.provider_factory import ProviderFactory
from calc.service_fee_calculator import ServiceFeeCalculator
from cli.client_manager import ClientManager
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from log_config import main_logger, init
from model.baking_conf import BakingConf
from util.dir_utils import get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir
from exception.configuration import ConfigurationException
from plugins import plugins
from util.process_life_cycle import ProcessLifeCycle

LINER = "--------------------------------------------"
NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger
life_cycle = ProcessLifeCycle()


def main(args):
    logger.info("TRD version {} is running in {} mode.".format(VERSION, "daemon" if args.background_service else "interactive"))
    logger.info("Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1)))

    publish_stats = not args.do_not_publish_stats
    logger.info("Anonymous statistics {} be collected. See docs/statistics.rst for more information."
                .format("will" if publish_stats else "will not"))

    # 1- find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 4. get network config
    client_manager = ClientManager(node_endpoint=args.node_endpoint,
                                   signer_endpoint=args.signer_endpoint)
    network_config_map = init_network_config(args.network, client_manager)
    network_config = network_config_map[args.network]
    logger.debug("Network config {}".format(network_config))

    # Setup provider to fetch RPCs
    provider_factory = ProviderFactory(args.reward_data_provider)

    # 5- load and verify baking configuration file
    config_file_path = None
    try:
        config_file_path = get_baking_configuration_file(config_dir)

        logger.info("Loading baking configuration file {}".format(config_file_path))

        parser = BakingYamlConfParser(yaml_text=ConfigParser.load_file(config_file_path),
                                      clnt_mngr=client_manager,
                                      provider_factory=provider_factory,
                                      network_config=network_config,
                                      node_url=args.node_endpoint,
                                      api_base_url=args.api_base_url)
        parser.parse()
        parser.validate()
        parser.process()

        # dictionary to BakingConf object, for a bit of type safety
        cfg_dict = parser.get_conf_obj()
        cfg = BakingConf(cfg_dict)

    except ConfigurationException as e:
        logger.info("Unable to parse '{}' config file.".format(config_file_path))
        logger.info(e)
        sys.exit(1)

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
    reports_base = os.path.expanduser(args.reports_base)

    # if in reports run mode, do not create consumers
    # create reports in reports directory
    if dry_run:
        reports_base = os.path.expanduser("./reports")

    reports_dir = os.path.join(reports_base, baking_address)

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

    # 10- load plugins
    plugins_manager = plugins.PluginManager(cfg.get_plugins_conf(), dry_run)

    # 11- Start producer and consumer
    p = PaymentProducer(name='producer',
                        initial_payment_cycle=args.initial_cycle,
                        network_config=network_config,
                        payments_dir=payments_root,
                        calculations_dir=calculations_root,
                        run_mode=RunMode(args.run_mode),
                        service_fee_calc=srvc_fee_calc,
                        release_override=args.release_override,
                        payment_offset=args.payment_offset,
                        baking_cfg=cfg,
                        life_cycle=life_cycle,
                        payments_queue=payments_queue,
                        dry_run=dry_run,
                        client_manager=client_manager,
                        node_url=args.node_endpoint,
                        reward_data_provider=args.reward_data_provider,
                        node_url_public=args.node_addr_public,
                        api_base_url=args.api_base_url,
                        retry_injected=args.retry_injected)
    p.start()

    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(name='consumer' + str(i),
                            payments_dir=payments_root,
                            key_name=payment_address,
                            payments_queue=payments_queue,
                            node_addr=args.node_endpoint,
                            client_manager=client_manager,
                            plugins_manager=plugins_manager,
                            rewards_type=cfg.get_rewards_type(),
                            args=args,
                            dry_run=dry_run,
                            reactivate_zeroed=cfg.get_reactivate_zeroed(),
                            delegator_pays_ra_fee=cfg.get_delegator_pays_ra_fee(),
                            delegator_pays_xfer_fee=cfg.get_delegator_pays_xfer_fee(),
                            dest_map=cfg.get_dest_map(),
                            network_config=network_config,
                            publish_stats=publish_stats)

        sleep(1)
        c.start()

        logger.info("Application start completed")
        logger.info(LINER)

    # Run forever
    try:
        while life_cycle.is_running():
            sleep(10)
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        life_cycle.do_shut_down()


def get_baking_configuration_file(config_dir):
    config_file = None
    for file in os.listdir(config_dir):
        if file.endswith(".yaml") and not file.startswith("master"):
            if config_file:
                raise Exception("Application only supports one baking configuration file. Found at least 2 {}, {}".format(config_file, file))
            config_file = file
    if config_file is None:
        raise Exception("Unable to find any '.yaml' configuration files inside configuration directory({})".format(config_dir))

    return os.path.join(config_dir, config_file)


if __name__ == '__main__2':

    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception("Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major, sys.version_info.minor))

    args = parse_arguments()

    init(args.syslog, args.log_file, args.verbose == 'on')

    print_banner(args, script_name="")

    main(args)

if __name__ == '__main__':
    life_cycle.start()