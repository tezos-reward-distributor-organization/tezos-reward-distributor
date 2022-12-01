from time import sleep

from log_config import main_logger
from Constants import (
    LINER,
)
from util.parser import build_parser
from util.args_validator import validate


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
    args = validate(parser)
    return args
