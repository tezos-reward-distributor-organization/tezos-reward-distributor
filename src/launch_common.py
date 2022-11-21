import os
import argparse
from time import sleep
import sys

from log_config import main_logger
from NetworkConfiguration import default_network_config_map
from Constants import (
    BASE_DIR,
    DEFAULT_LOG_FILE,
    PRIVATE_NODE_URL,
    PUBLIC_NODE_URL,
    PRIVATE_SIGNER_URL,
    REQUIREMENTS_FILE_PATH,
    LINER
)
from util.parser import build_parser


logger = main_logger


def print_banner(args, script_name):
    with open("./banner.txt", "rt") as file:
        print(file.read())
    print(LINER, flush=True)
    print("TRD Organization: Copyright 2021, see contributors.csv")
    print("huseyinabanox@gmail.com")
    print("Please leave copyright information")
    print(LINER, flush=True)

    sleep(0.1)

    print("Tezos Reward Distributor (TRD)" + script_name + " is Starting")


def parse_arguments(args=None):
    argparser = build_parser()
    args = argparser.parse_args()

    # Basic validations
    # You only have access to the parsed values after you parse_args()
    args = args_validation(args, argparser)
    # All passed
    return args


def args_validation(args, argparser):
    # Validate offset within known network defaults
    blocks_per_cycle = 0

    try:
        args.reward_data_provider
    except AttributeError:
        logger.info("args: reward_data_provider argument does not exist.")
    else:
        if args.reward_data_provider not in ["tzkt", "rpc"]:
            argparser.error(
                "reward_data_provider {:s} is not functional at the moment. Please use tzkt or rpc".format(
                    args.reward_data_provider
                )
            )

    try:
        args.network
    except AttributeError:
        logger.info("args: network argument does not exist.")
    else:
        network = args.network
        if network in default_network_config_map:
            blocks_per_cycle = default_network_config_map[network]["BLOCKS_PER_CYCLE"]

    try:
        args.payment_offset
    except AttributeError:
        logger.info("args: payment_offset argument does not exist.")
    else:
        payment_offset = args.payment_offset
        if not (payment_offset >= 0 and payment_offset < blocks_per_cycle):
            argparser.error(
                "Valid range for payment offset on {:s} is between 0 and {:d}.".format(
                    network, blocks_per_cycle
                )
            )

    try:
        args.initial_cycle
    except AttributeError:
        logger.info("args: initial_cycle argument does not exist.")
    else:
        initial_cycle = args.initial_cycle
        if initial_cycle < -1:
            argparser.error(
                "initial_cycle must be in the range of [-1,), default is -1 to start at last released cycle."
            )

    try:
        args.release_override
    except AttributeError:
        logger.info("args: release_override argument does not exist.")
    else:
        release_override = args.release_override
        preserved_cycles = default_network_config_map[network]["NB_FREEZE_CYCLE"]
        estimated_reward_override = -preserved_cycles * 2 - 1
        frozen_reward_override = -preserved_cycles
        if release_override not in [
            estimated_reward_override,
            frozen_reward_override,
            0,
        ]:
            argparser.error(
                f"For {network}, release-override must be {estimated_reward_override} (to pay estimated rewards), {frozen_reward_override} (to pay frozen rewards) or 0. Default is 0."
            )

    default_base_dir = os.path.normpath(BASE_DIR)
    default_log_file = os.path.join(
        os.path.normpath(BASE_DIR), os.path.normpath(DEFAULT_LOG_FILE)
    )

    # set possibly missing vital args
    try:
        args.base_directory
    except AttributeError:
        args.base_directory = default_base_dir

    try:
        args.log_file
    except AttributeError:
        args.log_file = default_log_file

    if args.base_directory != default_base_dir and args.log_file == default_log_file:
        args.log_file = os.path.join(
            os.path.normpath(args.base_directory), os.path.normpath(DEFAULT_LOG_FILE)
        )

    try:
        args.dry_run
    except AttributeError:
        logger.info("args: dry_run argument does not exist.")
        try:
            args.dry_run_no_consumers
        except AttributeError:
            logger.info("args: dry_run_no_consumers argument does not exist.")
        else:
            args.dry_run = args.dry_run_no_consumers
    else:
        try:
            args.dry_run_no_consumers
        except AttributeError:
            logger.info("args: dry_run_no_consumers argument does not exist.")
        else:
            args.dry_run = args.dry_run or args.dry_run_no_consumers

    return args

if __name__ == '__main__':
    main()
