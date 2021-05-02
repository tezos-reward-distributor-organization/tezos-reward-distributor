import sys
import pip
import pkg_resources

REQUIREMENTS_FILE_PATH = 'requirements.txt'


def requirements_installed(requirement_path=REQUIREMENTS_FILE_PATH):
    print("Checking installed packages ...")
    with open(requirement_path, 'r') as requirements:
        for requirement in requirements:
            try:
                pkg_resources.require(requirement)
            except Exception as e:
                requirement = requirement.replace('\n', '')
                print('The requirement {} was not found: {}\nWould you like to install {}? (y/n)'.format(requirement, e, requirement))
                value = input().lower()
                if value == 'y' and installed(requirement):
                    print("Please restart TRD!")
                else:
                    print("Please make sure to install all the required packages before using the TRD.\n"
                          "To install the requirements: 'pip3 install -r requirements.txt'\n")
                return False
        return True


def installed(package):
    if hasattr(pip, 'main'):
        pip.main(['install', package])
    else:
        pip._internal.main(['install', package])
    return True


def start_application(args=None):
    # Requirements need to be checked outside of the state machine
    # because the library transitions could not be present
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
