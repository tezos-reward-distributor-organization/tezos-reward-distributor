from log_config import main_logger
from NetworkConfiguration import default_network_config_map

import os
from Constants import (
    BASE_DIR,
    DEFAULT_LOG_FILE,
)


class ArgsValidator:

    def __init__(self, parser):
        self._parser = parser
        self._logger = main_logger
        self._args = parser.parse_known_args()[0]
        self._blocks_per_cycle = 0
        self._nb_freeze_cycle = 0

    def _reward_data_provider_validator(self):
        try:
            self._args.reward_data_provider
        except AttributeError:
            self._logger.info("args: reward_data_provider argument does not exist.")
        else:
            if self._args.reward_data_provider not in ["tzkt", "rpc"]:
                error_message = "reward_data_provider {:s} is not functional at the moment. Please use tzkt or rpc".format(
                    self._args.reward_data_provider
                )
                self._logger.info(error_message)
            return True

    def _network_validator(self):
        try:
            self._args.network
        except AttributeError:
            self._logger.info("args: network argument does not exist.")
        else:
            if self._args.network in default_network_config_map:
                self._blocks_per_cycle = default_network_config_map[
                    self._args.network]['BLOCKS_PER_CYCLE']
                self._nb_freeze_cycle = default_network_config_map[
                    self._args.network]['NB_FREEZE_CYCLE']
            return True

    def _base_directory_validator(self):
        default_base_dir = os.path.normpath(BASE_DIR)
        default_log_file = os.path.join(
            os.path.normpath(BASE_DIR), os.path.normpath(DEFAULT_LOG_FILE)
        )
        try:
            self._args.base_directory
        except AttributeError:
            self._args.base_directory = default_base_dir
        try:
            self._args.log_file
        except AttributeError:
            self._args.log_file = default_log_file

        if self._args.base_directory != default_base_dir and self._args.log_file == default_log_file:
            self._args.log_file = os.path.join(
                os.path.normpath(self._args.base_directory), os.path.normpath(
                    DEFAULT_LOG_FILE)
            )
        return True

    def _dry_run_validator(self):
        try:
            self._args.dry_run
        except AttributeError:
            self._logger.info("args: dry_run argument does not exist.")
        return True

    def _payment_offset_validator(self):
        try:
            self._args.payment_offset
        except AttributeError:
            self._logger.info("args: payment_offset argument does not exist.")
        else:
            if not (self._args.payment_offset >= 0 and self._args.payment_offset < self._blocks_per_cycle):
                self._parser.error(
                    "Valid range for payment offset on {:s} is between 0 and {:d}.".format(
                        self._args.network, self._blocks_per_cycle
                    )
                )
            return True

    def _initial_cycle_validator(self):
        try:
            self._args.initial_cycle
        except AttributeError:
            self._logger.info("args: initial_cycle argument does not exist.")
        else:
            if self._args.initial_cycle < -1:
                self._parser.error(
                    "initial_cycle must be in the range of [-1,), default is -1 to start at last released cycle."
                )
            return True

    def _release_override_validator(self):
        try:
            self._args.release_override
        except AttributeError:
            self._logger.info("args: release_override argument does not exist.")
        else:
            release_override = self._args.release_override
            preserved_cycles = self._nb_freeze_cycle
            estimated_reward_override = -preserved_cycles * 2 - 1
            frozen_reward_override = -preserved_cycles
            if release_override not in [
                estimated_reward_override,
                frozen_reward_override,
                0,
            ]:
                self._parser.error(
                    f"For {self._args.network}, release-override must be {estimated_reward_override} (to pay estimated rewards), {frozen_reward_override} (to pay frozen rewards) or 0. Default is 0."
                )
            return True

    def run_validation(self):
        self._reward_data_provider_validator()
        self._network_validator()
        self._base_directory_validator()
        self._payment_offset_validator()
        self._initial_cycle_validator()
        self._release_override_validator()
        return self._args


def validate(parser):
    validator = ArgsValidator(parser)
    return validator.run_validation()
