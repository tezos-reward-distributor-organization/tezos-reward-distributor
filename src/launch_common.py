from log_config import main_logger

LINER = "--------------------------------------------"
logger = main_logger

def print_banner(args, script_name):
    logger.info("Tezos Reward Distributor" + script_name + " is Starting")
    logger.info(LINER)
    logger.info("Copyright Huseyin ABANOZ 2019")
    logger.info("huseyinabanox@gmail.com")
    logger.info("Please leave copyright information")
    logger.info(LINER)
    if args.dry_run:
        logger.info("DRY RUN MODE")
        logger.info(LINER)

def add_argument_network(parser):
    parser.add_argument("-N", "--network", help="network name", choices=['ZERONET', 'ALPHANET', 'MAINNET'],
                        default='MAINNET')


def add_argument_reports_dir(parser):
    parser.add_argument("-r", "--reports_dir", help="Directory to create reports", default='~/pymnt/reports')


def add_argument_provider(parser):
    parser.add_argument("-P", "--reward_data_provider", help="where reward data is provided", choices=['tzscan', 'rpc'],
                        default='tzscan')


def add_argument_config_dir(parser):
    parser.add_argument("-f", "--config_dir", help="Directory to find baking configurations", default='~/pymnt/cfg')


def add_argument_node_addr(parser):
    parser.add_argument("-A", "--node_addr", help="Node host:port pair", default='127.0.0.1:8732')


def add_argument_dry(parser):
    parser.add_argument("-D", "--dry_run",
                        help="Run without injecting payments. Suitable for testing. Does not require locking.",
                        action="store_true")


def add_argument_dry_no_consumer(parser):
    parser.add_argument("-Dc", "--dry_run_no_consumers",
                        help="Run without any consumers. Suitable for testing. Does not require locking.",
                        action="store_true")


def add_argument_executable_dirs(parser):
    parser.add_argument("-E", "--executable_dirs",
                        help="Comma separated list of directories to search for client executable. Prefer single "
                             "location when setting client directory. If -d is set, point to location where tezos docker "
                             "script (e.g. mainnet.sh for mainnet) is found. Default value is given for minimum configuration effort.",
                        default='~/,~/tezos')


def add_argument_docker(parser):
    parser.add_argument("-d", "--docker",
                        help="Docker installation flag. When set, docker script location should be set in -E",
                        action="store_true")


def add_argument_verbose(parser):
    parser.add_argument("-V", "--verbose", help="Low level details.", action="store_true")
