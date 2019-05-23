import argparse
import json
import os
import queue
import sys
import time
from datetime import datetime

from cli.wallet_client_manager import WalletClientManager
from config.config_parser import ConfigParser
from config.yaml_conf_parser import YamlConfParser
from log_config import main_logger
from launch_common import print_banner, add_argument_network, add_argument_provider, add_argument_reports_dir, \
    add_argument_config_dir, add_argument_node_addr, add_argument_dry, add_argument_dry_no_consumer, \
    add_argument_executable_dirs, add_argument_docker, add_argument_verbose
from model.reward_log import RewardLog
from pay.payment_batch import PaymentBatch
from pay.payment_consumer import PaymentConsumer
from util.client_utils import get_client_path
from util.dir_utils import get_payment_root, \
    get_successful_payments_dir, get_failed_payments_dir
from util.process_life_cycle import ProcessLifeCycle

LINER = "--------------------------------------------"

NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger

life_cycle = ProcessLifeCycle()
MUTEZ = 1


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

    # 3- get client path

    client_path = get_client_path([x.strip() for x in args.executable_dirs.split(',')],
                                  args.docker, args.network,
                                  args.verbose)

    logger.debug("Tezos client path is {}".format(client_path))

    # 4- get client path
    client_path = get_client_path([x.strip() for x in args.executable_dirs.split(',')],
                                  args.docker, args.network,
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
    get_successful_payments_dir(payments_root, create=True)
    get_failed_payments_dir(payments_root, create=True)

    wllt_clnt_mngr = WalletClientManager(client_path, contracts_by_alias, addresses_by_pkh, managers)

    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(name='manual_payment_consumer', payments_dir=payments_root,
                            key_name=args.paymentaddress,
                            client_path=client_path, payments_queue=payments_queue, node_addr=args.node_addr,
                            wllt_clnt_mngr=wllt_clnt_mngr, verbose=args.verbose, dry_run=dry_run,
                            delegator_pays_xfer_fee=False)
        time.sleep(1)
        c.start()

    base_name_no_ext = os.path.basename(payments_file)
    base_name_no_ext = os.path.splitext(base_name_no_ext)[0]
    now = datetime.now()
    now_str = now.strftime("%Y%m%d%H%M%S")
    file_name = base_name_no_ext + "_" + now_str

    payment_items = []
    for key, value in payments_dict.items():
        pi = RewardLog.ExternalInstance(file_name, key, value)
        pi.payment = pi.payment * MUTEZ
        payment_items.append(pi)

        logger.info("Reward created for cycle %s address %s amount %f fee %f tz type %s",
                    pi.cycle, pi.address, pi.payment, pi.fee, pi.type)

    payments_queue.put(PaymentBatch(None, 0, payment_items))
    payments_queue.put(PaymentBatch(None, 0, [RewardLog.ExitInstance()]))


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
    add_argument_network(parser)
    add_argument_provider(parser)
    add_argument_reports_dir(parser)
    add_argument_config_dir(parser)
    add_argument_node_addr(parser)
    add_argument_dry(parser)
    add_argument_dry_no_consumer(parser)
    add_argument_executable_dirs(parser)
    add_argument_docker(parser)
    add_argument_verbose(parser)

    parser.add_argument("paymentaddress",
                        help="tezos account address (PKH) or an alias to make payments. If tezos signer is used "
                             "to sign for the address, it is necessary to use an alias.")
    parser.add_argument("payments_file", help="File of payment lines. Each line should contain PKH:amount. "
                                              "For example: KT1QRZLh2kavAJdrQ6TjdhBgjpwKMRfwCBmQ:123.33")


    args = parser.parse_args()
    script_name = " - Pay For Script"
    print_banner(args, script_name)

    main(args)
