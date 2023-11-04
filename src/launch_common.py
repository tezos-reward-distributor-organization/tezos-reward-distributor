import os
import sys
import pkg_resources
import subprocess

from time import sleep
from datetime import date

from Constants import (
    PYTHON_MAJOR,
    PYTHON_MINOR,
    LINER,
    NEW_PROTOCOL_DATE,
    NEW_PROTOCOL_NAME,
    REQUIREMENTS_FILE_PATH,
)


def python_version_ok(args=None):
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
    else:
        return True


def print_banner(args, script_name):
    with open("./banner.txt", "rt") as file:
        print(file.read())
    print(LINER, flush=True)
    print("TRD Organization: Copyright 2021, see contributors.csv")
    print("huseyinabanox@gmail.com")
    print("Please leave copyright information")
    print(LINER, flush=True)

    sleep(0.1)

    print("Tezos Reward Distributor (TRD)" + script_name + " is Starting")


def renamed_fee_ini(args=None):
    if os.path.isfile("fee.ini"):
        print(
            "File fee.ini is deprecated. You can change the values at src/pay/batch_payer.py."
        )
        print("File fee.ini is renamed to fee.ini.old?")
        try:
            os.rename("fee.ini", "fee.ini.old")
            print("File fee.ini has been renamed to fee.ini.old")
        except:
            print("Failed: File fee.ini needs to be manually deleted or renamed")
            return False
    return True


def new_protocol_live(args=None):
    today = date.today()
    print(("Current date: {}").format(today))
    print(("New protocol date: {}").format(NEW_PROTOCOL_DATE))
    if today >= NEW_PROTOCOL_DATE:
        print(
            (
                "Protocol {} could be live now. If it is live there are risks using this branch.\n"
                "It is suggested to reach out to the community to confirm, and switch to the new test branch \n"
                "or accept of the risks of using this branch".format(NEW_PROTOCOL_NAME)
            )
        )
        print("Do you want to continue using this branch? (y/N)")
        value = input().lower()
        if not value or value == "n":
            return True
    return False


def in_venv():
    return sys.prefix != sys.base_prefix


def installed(package):
    """
    The error status is 0. (bool(0) == False)
    The success status is 1. (bool(1) == True)
    """
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except:
        return False

    # if hasattr(pip, "main"):
    #    status_code = pip.main(["install", package])
    # else:
    #    status_code = pip._internal.main(["install", package])
    # return not bool(status_code)


def requirements_installed(requirement_path=REQUIREMENTS_FILE_PATH):
    if not in_venv():
        print(
            "Please make sure to activate a virtual environment for python due to breaking changes in Ubutu >= 23.XX:\n"
            "https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/ \n"
        )
        return False

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
            print("Would you like to install missing requirements? (Y/n)")
            value = input().lower()
            if not value or value == "y":
                success = True
                for r in missing_requirements:
                    success = success and installed(r)
                    if not success:
                        print("Could not install missing packages: {}\n".format(r))
                        break

            if value == "n" or not success:
                print(
                    "Please make sure to install all the required packages from 'requirements.txt' before using the TRD:\n"
                    "https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/ \n"
                )
                return False
            else:
                print("Requirements successfully installed!\n")
                return True
        else:
            print("... all dependencies available!\n")
            return True
    except (OSError, IOError) as e:
        print(
            "Error opening requirements.txt: {}\n"
            "Please make sure to install all the required packages from 'requirements.txt' before using the TRD:\n"
            "https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/ \n".format(
                e
            )
        )
        return False
