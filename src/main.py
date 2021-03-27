import sys

from log_config import main_logger
from util.process_life_cycle import ProcessLifeCycle

logger = main_logger

if __name__ == '__main__':
    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception("Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major, sys.version_info.minor))
    life_cycle = ProcessLifeCycle()
    life_cycle.start()