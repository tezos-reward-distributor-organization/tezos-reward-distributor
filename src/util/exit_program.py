import sys
from enum import Enum
from log_config import main_logger


class ExitCode(Enum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    USER_ABORT = 2


def exit_program(exit_code: ExitCode):
    main_logger.info("exit code: {}".format(exit_code.value))
    sys.exit(exit_code.value)
