import sys
from enum import Enum
from log_config import main_logger


class ExitCode(Enum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    USER_ABORT = 2
    SIGNER_ERROR = 3
    SIGNER_ERROR_NOT_RUNNING = 4
    NO_SPACE = 5
    INSUFFICIENT_FUNDS = 6


class ExitMessage(Enum):
    SIGNER_ERROR = "Unknown Error at signing. Please consult the verbose logs!"
    SIGNER_ERROR_NOT_RUNNING = "Error at signing. Make sure octez-signer is up and running 'octez-signer launch http signer'"


def exit_program(exit_code: ExitCode, exit_message: ExitMessage):
    main_logger.info("exit code: {}".format(exit_code.value))
    if exit_message(exit_code):
        main_logger.info("exit message: {}".format(exit_message.value))
    sys.exit(exit_code.value)
