import os
import sys
import pip
import pkg_resources
from datetime import date
from Constants import (
    PYTHON_MAJOR,
    PYTHON_MINOR,
    REQUIREMENTS_FILE_PATH,
    NEW_PROTOCOL_DATE,
    NEW_PROTOCOL_NAME,
)


def installed(package):
    """
    The error status is 0. (bool(0) == False)
    The success status is 1. (bool(1) == True)
    """
    if hasattr(pip, "main"):
        status_code = pip.main(["install", package])
    else:
        status_code = pip._internal.main(["install", package])
    return not bool(status_code)


def requirements_installed(requirement_path=REQUIREMENTS_FILE_PATH):
    print("Checking installed packages ...\n")
    missing_requirements = []
    try:
        with open(requirement_path, "r") as requirements:
            for requirement in requirements:
                try:
                    pkg_resources.require(requirement)
                except Exception as e:
                    requirement = requirement.replace("\n", "")
                    missing_requirements.append(requirement)
                    print(
                        "... requirement {} was not found: {}\n".format(requirement, e)
                    )
        if len(missing_requirements) > 0:
            print("Would you like to install missing requirements? (y/n)")
            value = input().lower()
            if value == "y":
                success = True
                for r in missing_requirements:
                    success = success and installed(r)
                if success:
                    print("Success: Please restart TRD!\n")
                else:
                    print("Error: Could not install missing packages!\n")

            if value != "y" or not success:
                print(
                    "Please make sure to install all the required packages before using the TRD.\n"
                    "To install the requirements: 'pip3 install -r requirements.txt'\n"
                )
            return False
        else:
            print("... all dependencies available!\n")
            return True
    except (OSError, IOError) as e:
        print(
            "Error opening requirements.txt: {}\n"
            "Please make sure to install all the required packages before using the TRD.\n"
            "To install the requirements: 'pip3 install -r requirements.txt'\n".format(
                e
            )
        )
        return False


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


def new_protocol_live(args=None):
    today = date.today()
    print(("Current date: {}").format(today))
    print(("TRD sunset date: {}").format(NEW_PROTOCOL_DATE))
    if today >= NEW_PROTOCOL_DATE:
        print(
            (
                "Protocol {} could be live now. If it is live there are risks using this branch.\n"
                "It is suggested to reach out to the community to confirm, and switch to the new test branch \n"
                "or be accept of the risks of using this branch".format(
                    NEW_PROTOCOL_NAME
                )
            )
        )
        print("Do you want to continue using this branch? (y/n) Default is n")
        value = input().lower()
        if not value:
            value = "n"
        if value == "y" or value == "Yes":
            return False
        if value == "n" or value == "No":
            return True
        else:
            new_protocol_live()
    return False


def start_application(args=None):
    if new_protocol_live():
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
    if not (
        sys.version_info.major >= PYTHON_MAJOR
        and sys.version_info.minor >= PYTHON_MINOR
    ):
        raise Exception(
            "Must be using Python {}.{} or later but it is {}.{}".format(
                PYTHON_MAJOR,
                PYTHON_MINOR,
                sys.version_info.major,
                sys.version_info.minor,
            )
        )
    start_application()
