import sys

from log_config import main_logger
from util.process_life_cycle import ProcessLifeCycle

logger = main_logger


def start_application(args):
    life_cycle = ProcessLifeCycle(args)
    life_cycle.start()


if __name__ == '__main__':
    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception("Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major, sys.version_info.minor))

    start_application(None)

    pass

