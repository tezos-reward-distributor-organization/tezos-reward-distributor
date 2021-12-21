import argparse
import json
import os
import queue
import sys
import time
from datetime import datetime

from cli.client_manager import ClientManager
from log_config import main_logger, init
from launch_common import (
    print_banner,
    add_argument_network,
    add_argument_provider,
    add_argument_reports_base,
    add_argument_config_dir,
    add_argument_node_endpoint,
    add_argument_dry,
    add_argument_dry_no_consumer,
    add_argument_signer_endpoint,
    add_argument_docker,
    add_argument_verbose,
)
from model.reward_log import RewardLog
from pay.payment_batch import PaymentBatch
from pay.payment_consumer import PaymentConsumer
from util.dir_utils import (
    get_payment_root,
    get_successful_payments_dir,
    get_failed_payments_dir,
)
from util.disk_is_full import disk_is_full
from util.process_life_cycle import ProcessLifeCycle

LINER = "--------------------------------------------"

NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger

life_cycle = ProcessLifeCycle()
MUTEZ = 1


def main(args):
    logger.info(
        "Arguments Configuration = {}".format(json.dumps(args.__dict__, indent=1))
    )

    # 1- find where configuration is
    config_dir = os.path.expanduser(args.config_dir)

    # create configuration directory if it is not present
    # so that user can easily put his configuration there
    if config_dir and not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # 3- load payments file
    payments_file = os.path.expanduser(args.payments_file)
    if not os.path.isfile(payments_file):
        raise Exception("payments_file ({}) does not exist.".format(payments_file))

    with open(payments_file, "r") as file:
        payment_lines = file.readlines()

    payments_dict = {}
    for line in payment_lines:
        pkh, amt = line.split(":")
        pkh = pkh.strip()
        amt = float(amt.strip())

        payments_dict[pkh] = amt

    if not payments_dict:
        raise Exception("No payments to process")

    # 6- is it a reports run
    dry_run = args.dry_run

    # 7- get reporting directories
    reports_dir = os.path.expanduser(args.reports_dir)

    # 8- Check the disk size at the reports dir location
    if disk_is_full(reports_dir):
        raise Exception(
            "Disk is full at {}. Please free space to continue saving reports.".format(
                reports_dir
            )
        )

    # if in reports run mode, do not create consumers
    # create reports in reports directory
    if dry_run:
        reports_dir = os.path.expanduser("./reports")

    reports_dir = os.path.join(reports_dir, "manual")

    payments_root = get_payment_root(reports_dir, create=True)
    get_successful_payments_dir(payments_root, create=True)
    get_failed_payments_dir(payments_root, create=True)

    client_manager = ClientManager(
        node_endpoint=args.node_endpoint, signer_endpoint=args.signer_endpoint
    )

    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(
            name="manual_payment_consumer",
            payments_dir=payments_root,
            key_name=args.paymentaddress,
            payments_queue=payments_queue,
            node_addr=args.node_endpoint,
            client_manager=client_manager,
            dry_run=dry_run,
            reactivate_zeroed=False,
            delegator_pays_ra_fee=False,
            delegator_pays_xfer_fee=False,
        )
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

        logger.info(
            "Reward created for cycle %s address %s amount %f fee %f tz type %s",
            pi.cycle,
            pi.address,
            pi.payment,
            pi.fee,
            pi.type,
        )

    payments_queue.put(PaymentBatch(None, 0, payment_items))
    payments_queue.put(PaymentBatch(None, 0, [RewardLog.ExitInstance()]))


def get_baking_configuration_file(config_dir):
    config_file = None
    for file in os.listdir(config_dir):
        if file.endswith(".yaml") and not file.startswith("master"):
            if config_file:
                raise Exception(
                    "Application only supports one baking configuration file. Found at least 2 {}, {}".format(
                        config_file, file
                    )
                )
            config_file = file
    if config_file is None:
        raise Exception(
            "Unable to find any '.yaml' configuration files inside configuration directory({})".format(
                config_dir
            )
        )

    return os.path.join(config_dir, config_file)


class ReleaseOverrideAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not -11 <= values:
            parser.error(
                "Valid range for release-override({0}) is [-11,) ".format(option_string)
            )

        setattr(namespace, "realase_override", values)


if __name__ == "__main__":

    if not sys.version_info.major >= 3 and sys.version_info.minor >= 6:
        raise Exception(
            "Must be using Python 3.6 or later but it is {}.{}".format(
                sys.version_info.major, sys.version_info.minor
            )
        )

    parser = argparse.ArgumentParser()
    add_argument_network(parser)
    add_argument_provider(parser)
    add_argument_reports_base(parser)
    add_argument_config_dir(parser)
    add_argument_node_endpoint(parser)
    add_argument_dry(parser)
    add_argument_dry_no_consumer(parser)
    add_argument_signer_endpoint(parser)
    add_argument_docker(parser)
    add_argument_verbose(parser)

    parser.add_argument(
        "paymentaddress",
        help="tezos account address (PKH) or an alias to make payments. If tezos signer is used "
        "to sign for the address, it is necessary to use an alias.",
    )
    parser.add_argument(
        "payments_file",
        help="File of payment lines. Each line should contain PKH:amount. "
        "For example: KT1QRZLh2kavAJdrQ6TjdhBgjpwKMRfwCBmQ:123.33",
    )

    args = parser.parse_args()

    init(args.syslog, args.log_file, args.verbose == "on", mode="payfor")

    script_name = " - Pay For Script"
    print_banner(args, script_name)

    main(args)
