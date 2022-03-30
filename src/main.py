import os
import sys
import pip
import pkg_resources
from datetime import date


REQUIREMENTS_FILE_PATH = "requirements.txt"
END_OF_SERVICE = date(2022, 4, 1)


def installed(package):
    """
    The success status is 0. (bool(0) == False)
    The error status is 1. (bool(1) == True)
    """
    if hasattr(pip, "main"):
        status_code = pip.main(["install", package])
    else:
        status_code = pip._internal.main(["install", package])
    return not bool(status_code)


def requirements_installed(requirement_path=REQUIREMENTS_FILE_PATH):
    print("Checking installed packages ...")
    with open(requirement_path, "r") as requirements:
        for requirement in requirements:
            try:
                pkg_resources.require(requirement)
            except Exception as e:
                requirement = requirement.replace("\n", "")
                print(
                    "The requirement {} was not found: {}\nWould you like to install {}? (y/n)".format(
                        requirement, e, requirement
                    )
                )
                value = input().lower()
                if value == "y" and installed(requirement):
                    print("Please restart TRD!")
                else:
                    print(
                        "Please make sure to install all the required packages before using the TRD.\n"
                        "To install the requirements: 'pip3 install -r requirements.txt'\n"
                    )
                return False
        return True


def check_fee_ini(args=None):
    # Check if the fee.ini configuration file is still present and, if so,
    # warn the user that the file has to be removed or renamed
    if os.path.isfile("fee.ini"):
        print(
            "File fee.ini is deprecated. You can change the values at src/pay/batch_payer.py."
        )
        print("Would you like to rename fee.ini to fee.ini.old? (y/n)")
        value = input().lower()
        if value == "yes" or value == "y":
            os.rename("fee.ini", "fee.ini.old")
            print("File fee.ini has been renamed to fee.ini.old")
        else:
            print("File fee.ini needs to be manually deleted or renamed")
    return 1


def check_ithaca_live(args=None):
    today = date.today()
    if today >= END_OF_SERVICE:
        print(
            "Ithaca protocol is live: Please switch branch to test and join Baking Slack for more information."
        )
        return True
    else:
        return False


def start_application(args=None):
    if check_ithaca_live():
        return 1
    check_fee_ini()

    # Requirements need to be checked outside of the state machine
    # because the library transitions could not be present
    if requirements_installed():
        from util.process_life_cycle import ProcessLifeCycle

        life_cycle = ProcessLifeCycle(args)
        life_cycle.start()
        return 0
    return 1


if __name__ == "__main__":
    # Check the python version
    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception(
            "Must be using Python 3.6 or later but it is {}.{}".format(
                sys.version_info.major, sys.version_info.minor
            )
        )

    start_application()
