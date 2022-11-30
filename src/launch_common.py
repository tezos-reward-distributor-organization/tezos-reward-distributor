import os
import argparse
from time import sleep

from log_config import main_logger
from NetworkConfiguration import default_network_config_map
from Constants import (
    BASE_DIR,
    DEFAULT_LOG_FILE,
    LINER,
)
from util.parser import build_parser
from util.args_validator import args_validator


logger = main_logger


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


def parse_arguments(args=None):
    parser = build_parser()
    # Basic validations
    # You only have access to the parsed values after you parse_args()
    args = args_validator(parser)
    # All passed
    return args
