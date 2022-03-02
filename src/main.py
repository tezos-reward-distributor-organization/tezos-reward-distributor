import os
import sys
import pip
import pkg_resources

from util.config_life_cycle import get_baking_cfg_file, do_set_up_dirs

REQUIREMENTS_FILE_PATH = "requirements.txt"


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


def check_migration_complete(args=None):
    # Check for successful data directory migration and guide user if config exists in old directory
    config_dir_old = os.path.expanduser("~/pymnt/cfg")
    reports_dir_old = os.path.expanduser("~/pymnt/reports")

    if config_dir_old and os.path.exists(config_dir_old):
        print("Old configuration folder found: {}".format(config_dir_old))
        print("Did you complete the data migration needed for TRD v11? (y/n)")
        value = input().lower()
        if value == "yes" or value == "y":
            print("To avoid this message delete the old folder structure.")
        else:
            raise Exception("Data must be migrated and folders deleted.")

    if reports_dir_old and os.path.exists(reports_dir_old):
        print("Old reports folder found: {}".format(reports_dir_old))
        print("Did you complete the data migration needed for TRD v11? (y/n)")
        value = input().lower()
        if value == "yes" or value == "y":
            print("To avoid this message delete the old folder structure.")
        else:
            raise Exception("Data must be migrated and folders deleted.")


def start_application(args=None):
    check_fee_ini()
    check_migration_complete()

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
