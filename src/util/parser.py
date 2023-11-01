import argparse
import os

from Constants import (
    BASE_DIR,
    CONFIG_DIR,
    REPORTS_DIR,
    SIMULATIONS_DIR,
    DEFAULT_LOG_FILE,
    CURRENT_TESTNET,
    PRIVATE_NODE_URL,
    PUBLIC_NODE_URL,
    PRIVATE_SIGNER_URL,
    DryRun,
)


# TODO: Properly format the help section, see: https://www.programcreek.com/python/example/51784/argparse.HelpFormatter
def build_parser():
    argparser = argparse.ArgumentParser(prog="TRD")
    add_argument_cycle(argparser)
    add_argument_mode(argparser)
    add_argument_adjusted_early_payouts(argparser)
    add_argument_payment_offset(argparser)
    add_argument_network(argparser)
    add_argument_node_endpoint(argparser)
    add_argument_provider(argparser)
    add_argument_node_addr_public(argparser)
    add_argument_base_directory(argparser)
    add_argument_dry(argparser)
    add_argument_signer_endpoint(argparser)
    add_argument_docker(argparser)
    add_argument_background_service(argparser)
    add_argument_stats(argparser)
    add_argument_verbose(argparser)
    add_argument_api_base_url(argparser)
    add_argument_retry_injected(argparser)
    add_argument_syslog(argparser)
    add_argument_log_file(argparser)
    return argparser


def add_argument_cycle(argparser):
    argparser.add_argument(
        "-C",
        "--initial_cycle",
        help="Cycle to start payment(s) from. "
        "Default value is -1: will pay rewards that were most recently released. "
        "Cycle for which rewards were most recently released is calculated based on the formula: "
        "current_cycle - 1 + [if --adjusted_payout_timing == True: (preserved_cycles + 1)] "
        "Valid range is [-1,).",
        default=-1,
        type=int,
    )


def add_argument_mode(argparser):
    argparser.add_argument(
        "-M",
        "--run_mode",
        help="Waiting decision after making pending payments. 1: default option. Run forever. "
        "2: Run all pending payments and exit. 3: Run for one cycle and exit. "
        "4: Retry all failed payments and exit. "
        "Recommended: Always explicitly specify starting cycle with -C",
        choices=[1, 2, 3, 4],
        default=1,
        type=int,
    )


def add_argument_adjusted_early_payouts(argparser):
    argparser.add_argument(
        "--adjusted_early_payouts",
        help="Overrides last released cycle (current_cycle - 1). Payment cycle will be "
        "(current_cycle - 1 + (preserved_cycles + 1)). Suitable for future payments later adjusted to reward_types actual or ideal. "
        "Add argument to trigger future payments. Its default value is False if not provided as argument.",
        action="store_true",
    )


def add_argument_payment_offset(argparser):
    argparser.add_argument(
        "-O",
        "--payment_offset",
        help="Number of blocks to wait after a cycle starts before starting payments. "
        "This can be useful because cycle beginnings may be busy.",
        default=0,
        type=int,
    )


def add_argument_network(argparser):
    argparser.add_argument(
        "-N",
        "--network",
        help="Network name. Default is MAINNET. The current test network is {0}.".format(
            CURRENT_TESTNET
        ),
        choices=["MAINNET", CURRENT_TESTNET],
        default="MAINNET",
    )


def add_argument_node_endpoint(argparser):
    argparser.add_argument(
        "-A",
        "--node_endpoint",
        help=(
            "Node (host:port pair) potentially with protocol prefix especially if TLS encryption is used. Default is {}. "
            "This is the main Tezos node used by the client for rpc queries and operation injections."
        ).format(PRIVATE_NODE_URL),
        default=PRIVATE_NODE_URL,
    )


def add_argument_provider(argparser):
    argparser.add_argument(
        "-P",
        "--reward_data_provider",
        help="Source of reward data. The default is 'tzkt' (TzKT API). "
        "Set to 'rpc' to use your own local node defined with the -A flag, "
        "(it must be an ARCHIVE node in this case). "
        "Set to 'prpc' to use a public RPC node defined with the -Ap flag. "
        "An alternative for providing reward data is 'tzpro', but an API key associated with your account needs to be provided in the .env file!",
        choices=["rpc", "prpc", "tzpro", "tzkt"],
        default="tzkt",
    )


def add_argument_node_addr_public(argparser):
    argparser.add_argument(
        "-Ap",
        "--node_addr_public",
        help=(
            "Public node base URL. Default is {}. "
            "This argument will only be used in case the reward provider is set to 'prpc'. "
            "This node will only be used to query reward data and delegator list. "
            "It must be an ARCHIVE node."
        ).format(PUBLIC_NODE_URL["MAINNET"]),
        default=PUBLIC_NODE_URL["MAINNET"],
    )


def add_argument_base_directory(argparser):
    default_dir = os.path.normpath(BASE_DIR)
    argparser.add_argument(
        "-b",
        "--base_directory",
        help=(
            "The base path for all TRD data. Default: {} "
            "The directory contains the following folders: "
            "1. {} "
            "2. {} "
            "3. {} "
            "4. {} "
            "Attention: Please make sure you have migrated the data accordingly from v10 onwards."
        ).format(
            default_dir,
            os.path.join(default_dir, CONFIG_DIR, ""),
            os.path.join(default_dir, SIMULATIONS_DIR, ""),
            os.path.join(default_dir, REPORTS_DIR, ""),
            os.path.dirname(os.path.join(default_dir, DEFAULT_LOG_FILE)),
        ),
        default=default_dir,
    )


def add_argument_dry(argparser):
    argparser.add_argument(
        "-D",
        "--dry_run",
        help="Run without injecting payments. Suitable for testing. Does not require locking. Options are: "
        f"1. {DryRun.SIGNER.value}(default): Use signer. "
        f"2. {DryRun.NO_SIGNER.value}: Do not use signer.",
        action="store",
        choices=[
            DryRun.SIGNER.value,
            DryRun.NO_SIGNER.value,
        ],
        default=False,
        const=DryRun.SIGNER.value,
        nargs="?",
    )


def add_argument_signer_endpoint(argparser):
    argparser.add_argument(
        "-E",
        "--signer_endpoint",
        help="URL used by the Tezos-signer to accept HTTP requests.",
        default=PRIVATE_SIGNER_URL,
    )


def add_argument_docker(argparser):
    argparser.add_argument(
        "-d",
        "--docker",
        help="Docker installation flag. When set, docker script location should be set in -E",
        action="store_true",
    )


def add_argument_background_service(argparser):
    argparser.add_argument(
        "-s",
        "--background_service",
        help="Marker to indicate that TRD is running in daemon mode. "
        "When not given it indicates that TRD is in interactive mode.",
        action="store_true",
    )


def add_argument_stats(argparser):
    argparser.add_argument(
        "-Dp",
        "--do_not_publish_stats",
        help="Do not publish anonymous usage statistics",
        action="store_true",
    )


def add_argument_verbose(argparser):
    argparser.add_argument(
        "-V",
        "--verbose",
        help="Produces a lot of logs. Good for trouble shooting. Verbose logs go into app_verbose log "
        "file. App verbose log file is named with cycle number and creation date. "
        "For each cycle a new file is created and old file is moved to archive_backup "
        "directory after being zipped.",
        choices=["on", "off"],
        default="on",
    )


def add_argument_api_base_url(argparser):
    argparser.add_argument(
        "-U",
        "--api_base_url",
        help="Base API url for non-rpc providers. If not set, public endpoints will be used.",
        type=str,
    )


def add_argument_retry_injected(argparser):
    argparser.add_argument(
        "-inj",
        "--retry_injected",
        help="Try to pay injected payment items. Use this option only if you are sure that payment items were injected but not actually paid.",
        action="store_true",
    )


def add_argument_syslog(argparser):
    argparser.add_argument(
        "--syslog", help="Log to syslog. Useful in daemon mode.", action="store_true"
    )


def add_argument_log_file(argparser):
    default_log_file = os.path.join(
        os.path.normpath(BASE_DIR), os.path.normpath(DEFAULT_LOG_FILE)
    )
    argparser.add_argument(
        "--log_file",
        help="Application log output folder path and file name. By default the logs are placed into the --base_directory e.g.: {}".format(
            default_log_file
        ),
        default=default_log_file,
    )
