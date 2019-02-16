import argparse
import argparse
import json
import os
import queue
import sys
import time
from datetime import datetime

from Constants import RunMode
from NetworkConfiguration import network_config_map
from calc.service_fee_calculator import ServiceFeeCalculator
from cli.wallet_client_manager import WalletClientManager
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from config.yaml_conf_parser import YamlConfParser
from log_config import main_logger
from model.baking_conf import BakingConf
from model.payment_log import PaymentRecord
from pay.payment_consumer import PaymentConsumer
from pay.payment_producer import PaymentProducer
from util.client_utils import get_client_path
from util.dir_utils import get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir
from util.process_life_cycle import ProcessLifeCycle

LINER = "--------------------------------------------"

NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger

life_cycle = ProcessLifeCycle()


def main(args):
    logger.info("Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1)))

    # 1- find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 2- Load master configuration file if it is present
    master_config_file_path = os.path.join(config_dir, "master.yaml")

    master_cfg = {}
    if os.path.isfile(master_config_file_path):
        logger.info("Loading master configuration file {}".format(master_config_file_path))

        master_parser = YamlConfParser(ConfigParser.load_file(master_config_file_path))
        master_cfg = master_parser.parse()
    else:
        logger.info("master configuration file not present.")

    managers = None
    contracts_by_alias = None
    addresses_by_pkh = None
    if 'managers' in master_cfg:
        managers = master_cfg['managers']
    if 'contracts_by_alias' in master_cfg:
        contracts_by_alias = master_cfg['contracts_by_alias']
    if 'addresses_by_pkh' in master_cfg:
        addresses_by_pkh = master_cfg['addresses_by_pkh']

    # 3- load payments file
    payments_file = os.path.expanduser(args.payments_file)
    if not os.path.isfile(payments_file):
        raise Exception("payments_file ({}) does not exist.".format(payments_file))

    with open(payments_file, 'r') as file:
        payment_lines = file.readlines()

    payments_dict = {}
    for line in payment_lines:
        pkh, amt = line.split(":")
        pkh = pkh.strip()
        amt = float(amt.strip())

        payments_dict[pkh] = amt

    if not payments_dict:
        raise Exception("No payments to process")

    # 4- get client path
    network_config = network_config_map[args.network]
    client_path = get_client_path([x.strip() for x in args.executable_dirs.split(',')],
                                  args.docker, network_config,
                                  args.verbose)

    logger.debug("Tezos client path is {}".format(client_path))

    # 6- is it a reports run
    dry_run = args.dry_run

    # 7- get reporting directories
    reports_dir = os.path.expanduser(args.reports_dir)
    # if in reports run mode, do not create consumers
    # create reports in reports directory
    if dry_run:
        reports_dir = os.path.expanduser("./reports")

    reports_dir = os.path.join(reports_dir, "manual")

    payments_root = get_payment_root(reports_dir, create=True)
    calculations_root = get_calculations_root(reports_dir, create=True)
    get_successful_payments_dir(payments_root, create=True)
    get_failed_payments_dir(payments_root, create=True)

    wllt_clnt_mngr = WalletClientManager(client_path, contracts_by_alias, addresses_by_pkh, managers)

    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(name='manual_payment_consumer', payments_dir=payments_root,
                            key_name=args.paymentaddress,
                            client_path=client_path, payments_queue=payments_queue, node_addr=args.node_addr,
                            wllt_clnt_mngr=wllt_clnt_mngr, verbose=args.verbose, dry_run=dry_run)
        time.sleep(1)
        c.start()

    base_name_no_ext = os.path.basename(payments_file)
    base_name_no_ext = os.path.splitext(base_name_no_ext)[0]
    now = datetime.now()
    now_str = now.strftime("%Y%m%d%H%M%S")
    file_name = base_name_no_ext + "_" + now_str

    payment_items = []
    for key, value in payments_dict.items():
        payment_items.append(PaymentRecord.ManualInstance(file_name, key, value))

    payments_queue.put(payment_items)
    payments_queue.put([PaymentRecord.ExitInstance()])


def get_baking_configuration_file(config_dir):
    config_file = None
    for file in os.listdir(config_dir):
        if file.endswith(".yaml") and not file.startswith("master"):
            if config_file:
                raise Exception(
                    "Application only supports one baking configuration file. Found at least 2 {}, {}".format(
                        config_file, file))
            config_file = file
    if config_file is None:
        raise Exception(
            "Unable to find any '.yaml' configuration files inside configuration directory({})".format(config_dir))

    return os.path.join(config_dir, config_file)


def get_latest_report_file(payments_root):
    recent = None
    if get_successful_payments_dir(payments_root):
        files = sorted([os.path.splitext(x)[0] for x in os.listdir(get_successful_payments_dir(payments_root))],
                       key=lambda x: int(x))
        recent = files[-1] if len(files) > 0 else None
    return recent


class ReleaseOverrideAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not -11 <= values:
            parser.error("Valid range for release-override({0}) is [-11,) ".format(option_string))

        setattr(namespace, "realase_override", values)


if __name__ == '__main__':

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    parser = argparse.ArgumentParser()
    parser.add_argument("paymentaddress",
                        help="tezos account address (PKH) or an alias to make payments. If tezos signer is used "
                             "to sign for the address, it is necessary to use an alias.")
    parser.add_argument("payments_file", help="File of payment lines. Each line should contain PKH:amount. "
                                              "For example: KT1QRZLh2kavAJdrQ6TjdhBgjpwKMRfwCBmQ:123.33")
    parser.add_argument("-N", "--network", help="network name", choices=['ZERONET', 'ALPHANET', 'MAINNET'],
                        default='MAINNET')
    parser.add_argument("-r", "--reports_dir", help="Directory to create reports", default='~/pymnt/reports')
    parser.add_argument("-f", "--config_dir", help="Directory to find baking configurations", default='~/pymnt/cfg')
    parser.add_argument("-A", "--node_addr", help="Node host:port pair", default='127.0.0.1:8732')
    parser.add_argument("-D", "--dry_run",
                        help="Run without injecting payments. Suitable for testing. Does not require locking.", default=True)
    parser.add_argument("-E", "--executable_dirs",
                        help="Comma separated list of directories to search for client executable. Prefer single "
                             "location when setting client directory. If -d is set, point to location where tezos docker "
                             "script (e.g. mainnet.sh for mainnet) is found. Default value is given for minimum configuration effort.",
                        default='~/,~/tezos')
    parser.add_argument("-d", "--docker",
                        help="Docker installation flag. When set, docker script location should be set in -E",
                        action="store_true")
    parser.add_argument("-V", "--verbose",
                        help="Low level details.",
                        action="store_true")

    args = parser.parse_args()

    logger.info("Tezos Reward Distributor Manual Payment Script Starting")
    logger.info(LINER)
    logger.info("Copyright Hüseyin ABANOZ 2019")
    logger.info("huseyinabanox@gmail.com")
    logger.info("Please leave copyright information")
    logger.info(LINER)
    if args.dry_run:
        logger.info("DRY RUN MODE")
        logger.info(LINER)
    main(args)
