from time import sleep
from NetworkConfiguration import default_network_config_map
from log_config import main_logger, DEFAULT_LOG_FILE

import argparse

LINER = "--------------------------------------------"
logger = main_logger


def print_banner(args, script_name):
    with open("./banner.txt", "rt") as file:
        print(file.read())
    print(LINER, flush=True)
    print("Copyright Huseyin ABANOZ 2019")
    print("huseyinabanox@gmail.com")
    print("Please leave copyright information")
    print(LINER, flush=True)

    sleep(0.1)

    logger.info("Tezos Reward Distributor" + script_name + " is Starting")

    if args.dry_run:
        logger.info(LINER)
        logger.info("DRY RUN MODE")
        logger.info(LINER)


def parse_arguments():
    parser = argparse.ArgumentParser()
    add_argument_cycle(parser)
    add_argument_mode(parser)
    add_argument_release_override(parser)
    add_argument_payment_offset(parser)
    add_argument_network(parser)
    add_argument_node_addr(parser)
    add_argument_provider(parser)
    add_argument_node_addr_public(parser)
    add_argument_reports_base(parser)
    add_argument_config_dir(parser)
    add_argument_dry(parser)
    add_argument_dry_no_consumer(parser)
    add_argument_executable_dirs(parser)
    add_argument_docker(parser)
    add_argument_background_service(parser)
    add_argument_stats(parser)
    add_argument_verbose(parser)
    add_argument_api_base_url(parser)
    add_argument_retry_injected(parser)
    add_argument_syslog(parser)
    add_argument_log_file(parser)

    args = parser.parse_args()

    #
    # Basic validations
    # You only have access to the parsed values after you parse_args()
    #

    # Validate offset within known network defaults
    network = args.network
    blocks_per_cycle = 0
    payment_offset = args.payment_offset
    if network in default_network_config_map:
        blocks_per_cycle = default_network_config_map[network]['BLOCKS_PER_CYCLE']
    if not (payment_offset >= 0 and payment_offset < blocks_per_cycle):
        parser.error("Valid range for payment offset on {:s} is between 0 and {:d}".format(
            network, blocks_per_cycle))

    # Verify cycle release override within range
    release_override = args.release_override
    if release_override < -11:
        parser.error("release-override cannot be less than -11")

    # All passed
    return args


def add_argument_cycle(parser):
    parser.add_argument("-C", "--initial_cycle",
                        help="First cycle to start payment. For last released rewards, set to 0. Non-positive values "
                             "are interpreted as: current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1). "
                             "If not set application will continue from last payment made or last reward released.",
                        type=int)


def add_argument_mode(parser):
    parser.add_argument("-M", "--run_mode",
                        help="Waiting decision after making pending payments. 1: default option. Run forever. "
                             "2: Run all pending payments and exit. 3: Run for one cycle and exit. "
                             "Suitable to use with -C option. 4: Retry failed payments and exit",
                        default=1, choices=[1, 2, 3, 4], type=int)


def add_argument_release_override(parser):
    parser.add_argument("-R", "--release_override",
                        help="Override NB_FREEZE_CYCLE value. last released payment cycle will be "
                             "(current_cycle-(NB_FREEZE_CYCLE+1)-release_override). Suitable for future payments. "
                             "For future payments give negative values. Valid range is [-11,)",
                        default=0, type=int)


def add_argument_payment_offset(parser):
    parser.add_argument("-O", "--payment_offset",
                        help="Number of blocks to wait after a cycle starts before starting payments. "
                             "This can be useful because cycle beginnings may be busy.",
                        default=0, type=int)


def add_argument_network(parser):
    parser.add_argument("-N", "--network",
                        help="Network name. Default is Mainnet. The test network of tezos is referred to as Alphanet even if the name changes with each protocol upgrade.",
                        choices=['MAINNET', 'ZERONET', 'ALPHANET'],
                        default='MAINNET')


def add_argument_node_addr(parser):
    parser.add_argument("-A", "--node_addr",
                        help="Node (host:port pair) potentially with protocol prefix especially if tls encryption is used. Default is http://127.0.0.1:8732. "
                             "This is the main Tezos node used by the client for rpc queries and operation injections.",
                        default='http://127.0.0.1:8732')


def add_argument_provider(parser):
    parser.add_argument("-P", "--reward_data_provider",
                        help="Source of reward data. The default is the use of a public archive rpc node, https://mainnet-tezos.giganode.io, to query all needed data for reward calculations. If you prefer to use your own local node defined with the -A flag for getting reward data please set the provider to rpc (the local node MUST be an ARCHIVE node in this case). If you prefer using a public rpc node, please set the node URL using the -Ap flag. An alternative for providing reward data is tzstats, but pay attention for license in case of COMMERCIAL use!!",
                        choices=['rpc', 'prpc', 'tzstats', 'tzkt'],
                        default='prpc')


def add_argument_node_addr_public(parser):
    parser.add_argument("-Ap", "--node_addr_public",
                        help="Public node base URL. This argument will only be used in case the provider is set to prpc. This node will only be used to query reward data and delegator list. It must be an ARCHIVE node. (Default is https://mainnet-tezos.giganode.io)",
                        default='')


def add_argument_reports_base(parser):
    parser.add_argument("-r", "--reports_base", help="Directory to create reports", default='~/pymnt/reports')


def add_argument_config_dir(parser):
    parser.add_argument("-f", "--config_dir", help="Directory to find baking configurations", default='~/pymnt/cfg')


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
                             "location when setting client directory. If -d is set, point to location where the tezos docker "
                             "script (e.g. mainnet.sh for mainnet) is found. Default value is given for minimum configuration effort.",
                        default='~/,~/tezos')


def add_argument_docker(parser):
    parser.add_argument("-d", "--docker",
                        help="Docker installation flag. When set, docker script location should be set in -E",
                        action="store_true")


def add_argument_background_service(parser):
    parser.add_argument("-s", "--background_service",
                        help="Marker to indicate that TRD is running in daemon mode. "
                             "When not given it indicates that TRD is in interactive mode.",
                        action="store_true")


def add_argument_stats(parser):
    parser.add_argument("-Dp", "--do_not_publish_stats",
                        help="Do not publish anonymous usage statistics",
                        action="store_true")


def add_argument_verbose(parser):
    parser.add_argument("-V", "--verbose",
                        help="Produces a lot of logs. Good for trouble shooting. Verbose logs go into app_verbose log "
                             "file. App verbose log file is named with cycle number and creation date. "
                             "For each cycle a new file is created and old file is moved to archive_backup "
                             "directory after being zipped.",
                        choices=['on', 'off'],
                        default='on')


def add_argument_api_base_url(parser: argparse.ArgumentParser):
    parser.add_argument("-U", "--api-base-url",
                        help="Base API url for non-rpc providers. If not set, public endpoints will be used.",
                        type=str)


def add_argument_retry_injected(parser):
    parser.add_argument("-inj", "--retry_injected",
                        help="Try to pay injected payment items. Use this option only if you are sure that payment items were injected but not actually paid.",
                        action="store_true")


def add_argument_syslog(parser):
    parser.add_argument("--syslog", help="Log to syslog. Useful in daemon mode.", action="store_true")


def add_argument_log_file(parser):
    parser.add_argument("--log-file", help="Log output file", default=DEFAULT_LOG_FILE)


def add_argument_syslog(parser):
    parser.add_argument("--syslog", help="Log to syslog. Useful in daemon mode.", action="store_true")


def add_argument_log_file(parser):
    parser.add_argument("--log-file", help="Log output file", default=DEFAULT_LOG_FILE)
