import json
import os
import queue
import sys
import time

from launch_common import print_banner, parse_arguments
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
from model.baking_conf import BakingConf
from pay.payment_consumer import PaymentConsumer
from pay.payment_producer import PaymentProducer
from util.client_utils import get_client_path
from util.dir_utils import get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir
from util.process_life_cycle import ProcessLifeCycle
from exception.configuration import ConfigurationException
from storage.storage import Storage
from storage.reports import ReportStorage
from storage.config import ConfigStorage, ConfigStorageException

LINER = "--------------------------------------------"
nb_consumers = 1
buf_size = 50
payments_queue = queue.Queue(buf_size)
logger = main_logger
life_cycle = ProcessLifeCycle()


def main(args):
    logger.info("TRD v{} - {} mode.".format(VERSION, "daemon" if args.background_service else "interactive"))
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

    # 3- get tezos-client path
    client_path = get_client_path([x.strip() for x in args.executable_dirs.split(',')],
                                  args.docker, args.network, args.verbose)

    logger.debug("Tezos client path is {}".format(client_path))

    # 4- get network config
    config_client_manager = SimpleClientManager(client_path, args.node_addr)
    network_config_map = init_network_config(args.network, config_client_manager, args.node_addr)
    network_config = network_config_map[args.network]

    logger.debug("Network config {}".format(network_config))

    # Load the payment wallet
    wllt_clnt_mngr = WalletClientManager(client_path, args.node_addr, contracts_by_alias, addresses_by_pkh, managers,
                                         verbose=args.verbose)

    # Setup provider to fetch RPCs
    provider_factory = ProviderFactory(args.reward_data_provider, verbose=args.verbose)

    # 5- is it a reports run
    dry_run = args.dry_run_no_consumers or args.dry_run
    if args.dry_run_no_consumers:
        nb_consumers = 0

    # 6- load and verify baking configuration from database
    try:

        block_api = provider_factory.newBlockApi(network_config, args.node_addr)

        db = Storage(config_dir, dry_run)

        # Look for old .yaml config file and convert to DB
        config_file_path = get_baking_configuration_file(config_dir)
        if config_file_path is not None:
            # 'None' indicates we have previously converted the .yaml to DB
            # if not None, then execute conf parser so we can save to DB

            logger.info("Converting baking configuration at {} to DB".format(config_file_path))

            parser = BakingYamlConfParser(ConfigParser.load_file(config_file_path), wllt_clnt_mngr,
                                          provider_factory, network_config, args.node_addr, verbose=args.verbose)
            parser.parse()
            yaml_cfg_dict = parser.get_conf_obj()

            # dictionary to BakingConf object, for a bit of type safety
            yaml_cfg = BakingConf(yaml_cfg_dict, master_cfg)
            yaml_cfg.validate(wllt_clnt_mngr, block_api)
            yaml_cfg.process()

            tmp_baking_address = yaml_cfg.get_baking_address()

            # Convert and store to DB
            ConfigStorage(db).save_baker_config(t_baking_address, yaml_cfg.toDB())

            # Move .yaml to .dbconverted so that we skip this on future runs
            move_baking_configuration_file(config_file_path)

        # Get config from DB
        db_cfg_dict = ConfigStorage(db).get_baker_config()
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

    # 7- start the life cycle
    life_cycle.start(not dry_run)

    # 8- service fee calculator
    srvc_fee_calc = ServiceFeeCalculator(db_cfg.get_full_supporters_set(), db_cfg.get_specials_map(),
                                         db_cfg.get_service_fee())

    # Determine the first cycle from where we will start processing, passed as flag or discovered from DB
    initial_cycle = args.initial_cycle
    if initial_cycle is None:
        # Fetch from DB, highest completed cycle
        recent_cycle = ReportStorage(storage).get_recent_cycle()

        # if payment logs exist, set initial cycle to the next cycle
        # if payment logs do not exists, set initial cycle to 0 so that payment starts from last released rewards
        initial_cycle = 0 if recent_cycle is None else int(recent_cycle) + 1

    logger.info("Initial cycle set to {}".format(initial_cycle))

    # Launch producer-consumer threads
    try:
        p = PaymentProducer(name='producer', initial_payment_cycle=initial_cycle, network_config=network_config,
                            run_mode=RunMode(args.run_mode),
                            service_fee_calc=srvc_fee_calc, release_override=args.release_override,
                            payment_offset=args.payment_offset, baking_cfg=db_cfg, life_cycle=life_cycle,
                            payments_queue=payments_queue, dry_run=dry_run, wllt_clnt_mngr=wllt_clnt_mngr,
                            node_url=args.node_addr, provider_factory=provider_factory, storage=storage,
                            node_url_public=args.node_addr_public, verbose=args.verbose)
        p.start()
    except Exception as e:
        logger.info("Unable to launch PaymentProducer")
        logger.info(e)
        sys.exit(1)

    publish_stats = not args.do_not_publish_stats
    for i in range(nb_consumers):
        c = PaymentConsumer(name='consumer' + str(i), storage=storage, key_name=payment_address,
                            client_path=client_path, payments_queue=payments_queue, node_addr=args.node_addr,
                            wllt_clnt_mngr=wllt_clnt_mngr, args=args, verbose=args.verbose, dry_run=dry_run,
                            reactivate_zeroed=db_cfg.get_reactivate_zeroed(),
                            delegator_pays_ra_fee=db_cfg.get_delegator_pays_ra_fee(),
                            delegator_pays_xfer_fee=db_cfg.get_delegator_pays_xfer_fee(), dest_map=db_cfg.get_dest_map(),
                            network_config=network_config, publish_stats=publish_stats)
        time.sleep(1)
        c.start()

        logger.info("Application start completed")
        logger.info(LINER)

    # Main check-sleep loop
    try:
        while life_cycle.is_running():
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        life_cycle.stop()


def get_baking_configuration_file(config_dir):
    config_file = None
    for file in os.listdir(config_dir):
        if file.endswith(".dbconverted"):
            logger.info("Found previously converted config file. Ignoring.")
            return None
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


def move_baking_configuration_file(config_file_path):
    try:
        os.replace(config_file_path, "{}.dbconverted".format(config_file_path))
        logger.info("Old config file converted to database. Renamed as backup.")
    except os.OSError as e:
        raise ConfigurationException("""Unable to rename old config after converting to database: {}
            Please remove '{}' manually.""".format(e, config_file_path)) from e


if __name__ == '__main__':

    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception("Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major, sys.version_info.minor))

    args = parse_arguments()

    print_banner(args, script_name="")

    main(args)
