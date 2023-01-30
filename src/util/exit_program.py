import sys
from enum import Enum


class ExitCode(Enum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    SYSTEM_FAILURE = 2
    CONFIGURATION_ERROR = 3
    FILE_NOT_FOUND = 4


def exit_program(exit_code: ExitCode):
    sys.exit(exit_code.value)
