import _thread
import argparse
import csv
import os
import queue
import sys
import threading
import time

from BusinessConfiguration import BAKING_ADDRESS, founders_map, owners_map, specials_map, STANDARD_FEE, MIN_DELEGATION_AMT, supporters_set
from BusinessConfigurationX import excluded_delegators_set, pymnt_scale
from Constants import RunMode
from NetworkConfiguration import network_config_map
from calc.payment_calculator import PaymentCalculator
from calc.service_fee_calculator import ServiceFeeCalculator
from log_config import main_logger
from model.payment_log import PaymentRecord
from pay.double_payment_check import check_past_payment
from pay.payment_consumer import PaymentConsumer
from tzscan.tzscan_block_api import TzScanBlockApiImpl
from tzscan.tzscan_reward_api import TzScanRewardApiImpl
from tzscan.tzscan_reward_calculator import TzScanRewardCalculatorApi
from util.client_utils import get_client_path
from util.dir_utils import PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR, BUSY_FILE, remove_busy_file, get_payment_root, \
    get_calculations_root, get_successful_payments_dir, get_failed_payments_dir, get_calculation_report_file
from util.process_life_cycle import ProcessLifeCycle
from util.rounding_command import RoundingCommand

NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger

lifeCycle = ProcessLifeCycle()


class ProducerThread(threading.Thread):
    def __init__(self, name, initial_payment_cycle, network_config, payments_dir, calculations_dir, run_mode,
                 service_fee_calc, deposit_owners_map, baker_founders_map, baking_address, batch, release_override,
                 payment_offset, excluded_delegators_set, min_delegation_amt, verbose=False):
        super(ProducerThread, self).__init__()
        self.baking_address = baking_address
        self.owners_map = deposit_owners_map
        self.founders_map = baker_founders_map
        self.excluded_set = excluded_delegators_set
        self.min_delegation_amt = min_delegation_amt
        self.name = name
        self.block_api = TzScanBlockApiImpl(network_config)
        self.fee_calc = service_fee_calc
        self.initial_payment_cycle = initial_payment_cycle
        self.nw_config = network_config
        self.payments_root = payments_dir
        self.calculations_dir = calculations_dir
        self.run_mode = run_mode
        self.exiting = False
        self.batch = batch
        self.release_override = release_override
        self.payment_offset = payment_offset
        self.verbose = verbose

        logger.debug('Producer started')

    def exit(self):
        if not self.exiting:
            payments_queue.put([self.create_exit_payment()])
            self.exiting = True

            _thread.interrupt_main()

    def run(self):
        current_cycle = self.block_api.get_current_cycle()

        payment_cycle = self.initial_payment_cycle

        # if non-positive initial_payment_cycle, set initial_payment_cycle to
        # 'current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1)'
        if self.initial_payment_cycle <= 0:
            payment_cycle = current_cycle - abs(self.initial_payment_cycle) - (
                    self.nw_config['NB_FREEZE_CYCLE'] + 1)
            logger.debug("Payment cycle is set to {}".format(payment_cycle))

        while lifeCycle.is_running():

            # take a breath
            time.sleep(5)

            logger.debug("Trying payments for cycle {}".format(payment_cycle))

            current_level = self.block_api.get_current_level(verbose=self.verbose)
            current_cycle = self.block_api.level_to_cycle(current_level)

            # create reports dir
            if self.calculations_dir and not os.path.exists(self.calculations_dir):
                os.makedirs(self.calculations_dir)

            logger.debug(
                "Checking for pending payments : payment_cycle <= current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override")
            logger.debug(
                "Checking for pending payments : checking {} <= {} - ({} + 1) - {}".format(payment_cycle, current_cycle,
                                                                                           self.nw_config[
                                                                                               'NB_FREEZE_CYCLE'],
                                                                                           self.release_override))

            # payments should not pass beyond last released reward cycle
            if payment_cycle <= current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override:
                if not payments_queue.full():
                    try:

                        logger.info("Payment cycle is " + str(payment_cycle))

                        # 1- get reward data
                        reward_api = TzScanRewardApiImpl(self.nw_config, self.baking_address)
                        reward_data = reward_api.get_rewards_for_cycle_map(payment_cycle, verbose=self.verbose)

                        # 2- make payment calculations from reward data
                        pymnt_logs, total_rewards = self.make_payment_calculations(payment_cycle, reward_data)

                        # 3- check for past payment evidence for current cycle
                        past_payment_state = check_past_payment(self.payments_root, payment_cycle)
                        if total_rewards > 0 and past_payment_state:
                            logger.warn(past_payment_state)
                            total_rewards = 0

                        # 4- if total_rewards > 0, proceed with payment
                        if total_rewards > 0:
                            report_file_path = get_calculation_report_file(self.calculations_dir, payment_cycle)

                            # 5- send to payment consumer
                            payments_queue.put(pymnt_logs)

                            # 6- create calculations report file. This file contains calculations details
                            self.create_calculations_report(payment_cycle, pymnt_logs, report_file_path, total_rewards)

                        # 7- next cycle
                        # processing of cycle is done
                        logger.info("Reward creation done for cycle %s", payment_cycle)
                        payment_cycle = payment_cycle + 1

                        # single run is done. Do not continue.
                        if self.run_mode == RunMode.ONETIME:
                            logger.info("Run mode ONETIME satisfied. Killing the thread ...")
                            self.exit()
                            break

                    except Exception:
                        logger.error("Error at reward calculation", exc_info=True)

                # end of queue size check
                else:
                    logger.debug("Wait a few minutes, queue is full")
                    # wait a few minutes to let payments done
                    time.sleep(60 * 3)
            # end of payment cycle check
            else:
                logger.debug(
                    "No pending payments for cycle {}, current cycle is {}".format(payment_cycle, current_cycle))
                # pending payments done. Do not wait any more.
                if self.run_mode == RunMode.PENDING:
                    logger.info("Run mode PENDING satisfied. Killing the thread ...")
                    self.exit()
                    break

                time.sleep(self.nw_config['BLOCK_TIME_IN_SEC'])

                self.retry_failed_payments()

                # calculate number of blocks until end of current cycle
                nb_blocks_remaining = (current_cycle + 1) * self.nw_config['BLOCKS_PER_CYCLE'] - current_level
                # plus offset. cycle beginnings may be busy, move payments forward
                nb_blocks_remaining = nb_blocks_remaining + self.payment_offset

                logger.debug("Wait until next cycle, for {} blocks".format(nb_blocks_remaining))

                # wait until current cycle ends
                self.waint_until_next_cycle(nb_blocks_remaining)

        # end of endless loop
        logger.info("Producer returning ...")

        # ensure consumer exits
        self.exit()

        return

    def waint_until_next_cycle(self, nb_blocks_remaining):
        for x in range(nb_blocks_remaining):
            time.sleep(self.nw_config['BLOCK_TIME_IN_SEC'])

            # if shutting down, exit
            if not lifeCycle.is_running():
                payments_queue.put([self.create_exit_payment()])
                break

    def create_calculations_report(self, payment_cycle, payment_logs, report_file_path, total_rewards):
        with open(report_file_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            # write headers and total rewards
            writer.writerow(["address", "type", "ratio", "reward", "fee_rate", "payment", "fee"])
            writer.writerow([self.baking_address, "B", 1.0, total_rewards, 0, total_rewards, 0])

            for pymnt_log in payment_logs:
                # write row to csv file
                writer.writerow([pymnt_log.address, pymnt_log.type,
                                 "{0:f}".format(pymnt_log.ratio),
                                 "{0:f}".format(pymnt_log.reward),
                                 "{0:f}".format(pymnt_log.fee_rate),
                                 "{0:f}".format(pymnt_log.payment),
                                 "{0:f}".format(pymnt_log.fee)])

                logger.info("Reward created for cycle %s address %s amount %f fee %f tz type %s",
                            payment_cycle, pymnt_log.address, pymnt_log.payment, pymnt_log.fee,
                            pymnt_log.type)

    def make_payment_calculations(self, payment_cycle, reward_data):

        if reward_data["delegators_nb"] == 0:
            logger.warn("No delegators at cycle {}. Check your delegation status".format(payment_cycle))
            return [], 0

        reward_calc = TzScanRewardCalculatorApi(self.founders_map, reward_data, self.min_delegation_amt, excluded_delegators_set)

        rewards, total_rewards = reward_calc.calculate()

        logger.info("Total rewards={}".format(total_rewards))

        if total_rewards == 0: return [], 0
        fm, om = self.founders_map, self.owners_map
        rouding_command = RoundingCommand(pymnt_scale)
        pymnt_calc = PaymentCalculator(fm, om, rewards, total_rewards, self.fee_calc, payment_cycle, rouding_command)
        payment_logs = pymnt_calc.calculate()

        return payment_logs, total_rewards

    @staticmethod
    def create_exit_payment():
        return PaymentRecord.ExitInstance()

    def retry_failed_payments(self):
        logger.info("retry_failed_payments started")

        # 1 - list csv files under payments/failed directory
        # absolute path of csv files found under payments_root/failed directory
        failed_payments_dir = get_failed_payments_dir(self.payments_root)
        payment_reports_failed = [os.path.join(failed_payments_dir, x) for x in
                                  os.listdir(failed_payments_dir) if x.endswith('.csv')]

        logger.debug("Trying failed payments : '{}'".format(",".join(payment_reports_failed)))

        # 2- for each csv file with name csv_report.csv
        for payment_failed_report_file in payment_reports_failed:
            logger.debug("Working on failed payment file {}".format(payment_failed_report_file))

            # 2.1 - if there is a file csv_report.csv under payments/done, it means payment is already done
            if os.path.isfile(payment_failed_report_file.replace(PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR)):
                # remove payments/failed/csv_report.csv
                os.remove(payment_failed_report_file)
                logger.debug(
                    "Payment for failed payment {} is already done. Removing.".format(payment_failed_report_file))

                # remove payments/failed/csv_report.csv.BUSY
                # if there is a busy failed payment report file, remove it.
                remove_busy_file(payment_failed_report_file)

                # do not double pay
                continue

            # 2.2 - if queue is full, wait for sometime
            # make sure the queue is not full
            while payments_queue.full():
                logger.info("Payments queue is full. Wait a few minutes.")
                time.sleep(60 * 3)

            cycle = int(os.path.splitext(os.path.basename(payment_failed_report_file))[0])

            # 2.3 read payments/failed/csv_report.csv file into a list of dictionaries
            with open(payment_failed_report_file) as f:
                # read csv into list of dictionaries
                dict_rows = [{key: value for key, value in row.items()} for row in
                             csv.DictReader(f, skipinitialspace=True)]

                batch = PaymentRecord.FromPaymentCSVDictRows(dict_rows, cycle)

                # 2.4 put records into payment_queue. payment_consumer will make payments
                payments_queue.put(batch)

                # 2.5 rename payments/failed/csv_report.csv to payments/failed/csv_report.csv.BUSY
                # mark the files as in use. we do not want it to be read again
                # BUSY file will be removed, if successful payment is done
                os.rename(payment_failed_report_file, payment_failed_report_file + BUSY_FILE)


# all shares in the map must sum up to 1
def validate_map_share_sum(share_map, map_name):
    if len(share_map) > 0:
        if abs(1 - sum(share_map.values()) > 1e-4):  # a zero check actually
            raise Exception("Map '{}' shares does not sum up to 1!".format(map_name))


def main(config):
    network_config = network_config_map[config.network]
    key = config.paymentaddress

    dry_run = config.dry_run_no_payments or config.dry_run
    if config.dry_run_no_payments:
        global NB_CONSUMERS
        NB_CONSUMERS = 0

    reports_dir = os.path.expanduser(config.reports_dir)
    # if in dry run mode, do not create consumers
    # create reports in dry directory
    if dry_run:
        reports_dir = os.path.expanduser("./dry")

    payments_root = get_payment_root(reports_dir, create=True)
    calculations_root = get_calculations_root(reports_dir, create=True)
    get_successful_payments_dir(payments_root, create=True)
    get_failed_payments_dir(payments_root, create=True)

    run_mode = RunMode(config.run_mode)
    node_addr = config.node_addr
    payment_offset = config.payment_offset

    client_path = get_client_path([x.strip() for x in config.executable_dirs.split(',')], config.docker, network_config,
                                  config.verbose)
    logger.debug("Client command is {}".format(client_path))

    validate_map_share_sum(founders_map, "founders map")
    validate_map_share_sum(owners_map, "owners map")

    lifeCycle.start(not dry_run)

    global supporters_set
    global excluded_delegators_set

    if not supporters_set:  # empty sets are evaluated as dict
        supporters_set = set()

    if not excluded_delegators_set:  # empty sets are evaluated as dict
        excluded_delegators_set = set()

    full_supporters_set = supporters_set | set(founders_map.keys()) | set(owners_map.keys())

    service_fee_calc = ServiceFeeCalculator(supporters_set=full_supporters_set, specials_map=specials_map,
                                            standard_fee=STANDARD_FEE)

    if config.initial_cycle is None:
        recent = None
        if get_successful_payments_dir(payments_root):
            files = sorted([os.path.splitext(x)[0] for x in os.listdir(get_successful_payments_dir(payments_root))],
                           key=lambda x: int(x))
            recent = files[-1] if len(files) > 0 else None
        # if payment logs exists set initial cycle to following cycle
        # if payment logs does not exists, set initial cycle to 0, so that payment starts from last released rewards
        config.initial_cycle = 0 if recent is None else int(recent) + 1

        logger.info("initial_cycle set to {}".format(config.initial_cycle))

    p = ProducerThread(name='producer', initial_payment_cycle=config.initial_cycle, network_config=network_config,
                       payments_dir=payments_root, calculations_dir=calculations_root, run_mode=run_mode,
                       service_fee_calc=service_fee_calc, deposit_owners_map=owners_map,
                       baker_founders_map=founders_map, baking_address=BAKING_ADDRESS, batch=config.batch,
                       release_override=config.release_override, payment_offset=payment_offset,
                       excluded_delegators_set=excluded_delegators_set, min_delegation_amt=MIN_DELEGATION_AMT, verbose=config.verbose)
    p.start()

    for i in range(NB_CONSUMERS):
        c = PaymentConsumer(name='consumer' + str(i), payments_dir=payments_root, key_name=key,
                            client_path=client_path, payments_queue=payments_queue, node_addr=node_addr,
                            verbose=config.verbose, dry_run=dry_run)
        time.sleep(1)
        c.start()
    try:
        while lifeCycle.is_running(): time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Interrupted.")
        lifeCycle.stop()


if __name__ == '__main__':

    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")

    parser = argparse.ArgumentParser()
    parser.add_argument("paymentaddress", help="tezos account address (PKH) or an alias to make payments. If tezos signer is used "
                                    "to sign for the address, it is necessary to use an alias.")
    parser.add_argument("-N", "--network", help="network name", choices=['ZERONET', 'ALPHANET', 'MAINNET'],
                        default='MAINNET')
    parser.add_argument("-r", "--reports_dir", help="Directory to create reports", default='./reports')
    parser.add_argument("-A", "--node_addr", help="Node host:port pair", default='127.0.0.1:8732')
    parser.add_argument("-D", "--dry_run",
                        help="Run without injecting payments. Suitable for testing. Does not require locking.",
                        action="store_true")
    parser.add_argument("-Dn", "--dry_run_no_payments",
                        help="Run without doing any payments. Suitable for testing. Does not require locking.",
                        action="store_true")
    parser.add_argument("-B", "--batch",
                        help="Make batch payments.",
                        action="store_true")
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
    parser.add_argument("-M", "--run_mode",
                        help="Waiting decision after making pending payments. 1: default option. Run forever. "
                             "2: Run all pending payments and exit. 3: Run for one cycle and exit. "
                             "Suitable to use with -C option.",
                        default=1, choices=[1, 2, 3], type=int)
    parser.add_argument("-R", "--release_override",
                        help="Override NB_FREEZE_CYCLE value. last released payment cycle will be "
                             "(current_cycle-(NB_FREEZE_CYCLE+1)-release_override). Suitable for future payments. "
                             "For future payments give negative values. ",
                        default=0, type=int)
    parser.add_argument("-O", "--payment_offset",
                        help="Number of blocks to wait after a cycle starts before starting payments. "
                             "This can be useful because cycle beginnings may be bussy.",
                        default=0, type=int)
    parser.add_argument("-C", "--initial_cycle",
                        help="First cycle to start payment. For last released rewards, set to 0. Non-positive values "
                             "are interpreted as : current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1). "
                             "If not set application will continue from last payment made or last reward released.",
                        type=int)

    args = parser.parse_args()

    logger.info("Tezos Reward Distributor is Starting")
    logger.info("Current network is {}".format(args.network))
    logger.info("Baker address is {}".format(BAKING_ADDRESS))
    logger.info("Payment address is {}".format(args.paymentaddress))
    logger.info("--------------------------------------------")
    logger.info("Copyright Hüseyin ABANOZ 2018")
    logger.info("huseyinabanox@gmail.com")
    logger.info("Please leave copyright information")
    logger.info("--------------------------------------------")
    if args.dry_run:
        logger.info("DRY RUN MODE")
        logger.info("--------------------------------------------")
    main(args)
