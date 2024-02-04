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
    RETRY_FAILED = 7
    PROVIDER_ERROR = 8


def exit_program(exit_code: ExitCode = ExitCode.SUCCESS, exit_message="Success!"):
    main_logger.info(f"{exit_message}, exit code: {exit_code.value}")
    sys.exit(exit_code.value)
