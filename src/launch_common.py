from time import sleep

from log_config import main_logger

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
    print(LINER,flush=True)

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
    args = parser.parse_args()
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
                             "Suitable to use with -C option.",
                        default=1, choices=[1, 2, 3], type=int)


class ReleaseOverrideAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not -11 <= values:
            parser.error("Valid range for release-override({0}) is [-11,) ".format(option_string))

        setattr(namespace, "release_override", values)


def add_argument_release_override(parser):
    parser.add_argument("-R", "--release_override",
                        help="Override NB_FREEZE_CYCLE value. last released payment cycle will be "
                             "(current_cycle-(NB_FREEZE_CYCLE+1)-release_override). Suitable for future payments. "
                             "For future payments give negative values. Valid range is [-11,)",
                        default=0, type=int, action=ReleaseOverrideAction)


def add_argument_payment_offset(parser):
    parser.add_argument("-O", "--payment_offset",
                        help="Number of blocks to wait after a cycle starts before starting payments. "
                             "This can be useful because cycle beginnings may be busy.",
                        default=0, type=int)


def add_argument_network(parser):
    parser.add_argument("-N", "--network", help="Network name. Default is Mainnet. The test network of tezos is referred to as Alphanet even if the name changes with each protocol upgrade.",
                        choices=['MAINNET', 'ZERONET', 'ALPHANET'],
                        default='MAINNET')


def add_argument_node_addr(parser):
    parser.add_argument("-A", "--node_addr", help="Node (host:port pair). Default is 127.0.0.1:8732. This is the main Tezos node used by the client for rpc queries and operation injections.", default='127.0.0.1:8732')


def add_argument_provider(parser):
    parser.add_argument("-P", "--reward_data_provider", help="Source of reward data. The default is the use of a public archive rpc node, https://mainnet-tezos.giganode.io, to query all needed data for reward calculations. If you prefer to use your own local node defined with the -A flag for getting reward data please set the provider to rpc (the local node MUST be an ARCHIVE node in this case). If you prefer using a public rpc node, please set the node URL using the -Ap flag. An alternative for providing reward data is tzstats, but pay attention for license in case of COMMERCIAL use!!", choices=['rpc','prpc','tzstats'],
                        default='prpc')


def add_argument_node_addr_public(parser):
    parser.add_argument("-Ap", "--node_addr_public", help="Public node base URL. This argument will only be used in case the provider is set to prpc. This node will only be used to query reward data and delegator list. It must be an ARCHIVE node. (Default is https://mainnet-tezos.giganode.io)", default='')


def add_argument_reports_base(parser):
    parser.add_argument("-r", "--reports_base", help="Directory to create reports", default='~/pymnt/reports')


def add_argument_config_dir(parser):
    parser.add_argument("-f", "--config_dir", help="Directory to store configuration database", default='~/pymnt/cfg')


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
    parser.add_argument("-V", "--verbose", help="Produces a lot of logs. Good for trouble shooting.", action="store_true")
