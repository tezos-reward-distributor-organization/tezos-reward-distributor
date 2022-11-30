from log_config import main_logger
from NetworkConfiguration import default_network_config_map

import os
from Constants import (
    BASE_DIR,
    DEFAULT_LOG_FILE,
)


def reward_data_provider_validator(args):
    logger = main_logger
    try:
        args.reward_data_provider
    except AttributeError:
        logger.info("args: reward_data_provider argument does not exist.")
    else:
        if args.reward_data_provider not in ["tzkt", "rpc"]:
            error_message = "reward_data_provider {:s} is not functional at the moment. Please use tzkt or rpc".format(
                args.reward_data_provider
            )
            logger.info(error_message)


def network_validator(args):
    logger = main_logger
    try:
        args.network
    except AttributeError:
        logger.info("args: network argument does not exist.")
    else:
        network_args = dict()
        network_args['NAME'] = args.network
        if args.network in default_network_config_map:
            network_args['BLOCKS_PER_CYCLE'] = default_network_config_map[args.network]["BLOCKS_PER_CYCLE"]
        return network_args


def base_directory_validator(args):
    default_base_dir = os.path.normpath(BASE_DIR)
    default_log_file = os.path.join(
        os.path.normpath(BASE_DIR), os.path.normpath(DEFAULT_LOG_FILE)
    )
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
    return args


def dry_run_validator(args):
    logger = main_logger
    try:
        args.dry_run
    except AttributeError:
        logger.info("args: dry_run argument does not exist.")


def payment_offset_validator(argparser, args, blocks_per_cycle, network):
    logger = main_logger
    try:
        args.payment_offset
    except AttributeError:
        logger.info("args: payment_offset argument does not exist.")
    else:
        if not (args.payment_offset >= 0 and args.payment_offset < blocks_per_cycle):
            argparser.error(
                "Valid range for payment offset on {:s} is between 0 and {:d}.".format(
                    network, blocks_per_cycle
                )
            )


def initial_cycle_validator(argparser, args):
    logger = main_logger
    try:
        args.initial_cycle
    except AttributeError:
        logger.info("args: initial_cycle argument does not exist.")
    else:
        if args.initial_cycle < -1:
            argparser.error(
                "initial_cycle must be in the range of [-1,), default is -1 to start at last released cycle."
            )


def release_override_validator(argparser, args, nb_freeze_cycle, network):
    logger = main_logger
    try:
        args.release_override
    except AttributeError:
        logger.info("args: release_override argument does not exist.")
    else:
        release_override = args.release_override
        preserved_cycles = nb_freeze_cycle
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


def args_validator(parser):
    args = parser.parse_args()
    reward_data_provider_validator(args)
    network = network_validator(args)
    payment_offset_validator(
        parser, args, network['BLOCKS_PER_CYCLE'], network['NAME']
    )
    initial_cycle_validator(parser, args)
    release_override_validator(
        parser, args, default_network_config_map[args.network]["NB_FREEZE_CYCLE"], network['NAME']
    )
    dry_run_validator(args)
    return base_directory_validator(args)
