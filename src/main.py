import sys
from launch_common import requirements_installed


def start_application(args=None):
    if requirements_installed():
        from util.process_life_cycle import ProcessLifeCycle
        life_cycle = ProcessLifeCycle(args)
        life_cycle.start()
        return 0
    return 1


if __name__ == '__main__':
    # Check the python version
    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception("Must be using Python 3.6 or later but it is {}.{}".format(sys.version_info.major, sys.version_info.minor))

    start_application()
