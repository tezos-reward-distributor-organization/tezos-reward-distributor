import _thread
import csv
import os
import threading
import time

from Constants import RunMode
from calc.phased_payment_calculator import PhasedPaymentCalculator
from log_config import main_logger
from model.payment_log import PaymentRecord
from model.rules_model import RulesModel
from pay.double_payment_check import check_past_payment
from thirdparty.tzscan.tzscan_block_api import TzScanBlockApiImpl
from thirdparty.tzscan.tzscan_reward_provider import TzScanRewardProvider
from util.dir_utils import get_calculation_report_file, get_failed_payments_dir, PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR, \
    remove_busy_file, BUSY_FILE
from util.rounding_command import RoundingCommand

logger = main_logger

MUTEZ = 1e+6


class PaymentProducer(threading.Thread):
    def __init__(self, name, initial_payment_cycle, network_config, payments_dir, calculations_dir, run_mode,
                 service_fee_calc, release_override, payment_offset, baking_cfg, payments_queue, life_cycle,
                 dry_run, verbose=False):
        super(PaymentProducer, self).__init__()
        self.rules_model = RulesModel(baking_cfg.get_excluded_set_tob(),baking_cfg.get_excluded_set_toe(),baking_cfg.get_excluded_set_tof(),baking_cfg.get_dest_map())
        self.baking_address = baking_cfg.get_baking_address()
        self.owners_map = baking_cfg.get_owners_map()
        self.founders_map = baking_cfg.get_founders_map()
        self.min_delegation_amt_in_mutez = baking_cfg.get_min_delegation_amount() * MUTEZ
        self.pymnt_scale = baking_cfg.get_payment_scale()
        self.prcnt_scale = baking_cfg.get_percentage_scale()

        self.name = name
        self.block_api = TzScanBlockApiImpl(network_config)
        self.fee_calc = service_fee_calc
        self.initial_payment_cycle = initial_payment_cycle
        self.nw_config = network_config
        self.payments_root = payments_dir
        self.calculations_dir = calculations_dir
        self.run_mode = run_mode
        self.exiting = False

        self.release_override = release_override
        self.payment_offset = payment_offset
        self.verbose = verbose
        self.payments_queue = payments_queue
        self.life_cycle = life_cycle
        self.dry_run = dry_run
        logger.debug('Producer started')

    def exit(self):
        if not self.exiting:
            self.payments_queue.put([self.create_exit_payment()])
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

        while self.life_cycle.is_running():

            # take a breath
            time.sleep(5)

            logger.debug("Trying payments for cycle {}".format(payment_cycle))

            current_level = self.block_api.get_current_level(verbose=self.verbose)
            current_cycle = self.block_api.level_to_cycle(current_level)

            # create reports dir
            if self.calculations_dir and not os.path.exists(self.calculations_dir):
                os.makedirs(self.calculations_dir)

            logger.debug("Checking for pending payments : payment_cycle <= "
                         "current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override")
            logger.debug(
                "Checking for pending payments : checking {} <= {} - ({} + 1) - {}".
                    format(payment_cycle, current_cycle, self.nw_config['NB_FREEZE_CYCLE'], self.release_override))

            # payments should not pass beyond last released reward cycle
            if payment_cycle <= current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override:
                if not self.payments_queue.full():
                    try:

                        logger.info("Payment cycle is " + str(payment_cycle))

                        # 1- get reward data
                        reward_provider = TzScanRewardProvider(self.nw_config, self.baking_address)
                        reward_provider_model = reward_provider.provide_for_cycle(payment_cycle, self.verbose)

                        # 2- calculate rewards
                        prcnt_rm = RoundingCommand(self.prcnt_scale)
                        pymnt_rm = RoundingCommand(self.pymnt_scale)

                        payment_calc = PhasedPaymentCalculator(self.founders_map, self.owners_map,
                                                               self.fee_calc, payment_cycle, prcnt_rm, pymnt_rm,
                                                               self.min_delegation_amt_in_mutez, self.rules_model)
                        reward_logs, total_amount = payment_calc.calculate(reward_provider_model)

                        # 3- check for past payment evidence for current cycle
                        past_payment_state = check_past_payment(self.payments_root, payment_cycle)
                        if not self.dry_run and total_amount > 0 and past_payment_state:
                            logger.warn(past_payment_state)
                            total_amount = 0

                        # 4- if total_rewards > 0, proceed with payment
                        if total_amount > 0:
                            report_file_path = get_calculation_report_file(self.calculations_dir, payment_cycle)

                            # 5- send to payment consumer
                            self.payments_queue.put(reward_logs)

                            # 6- create calculations report file. This file contains calculations details
                            self.create_calculations_report(payment_cycle, reward_logs, report_file_path, total_amount)

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
            if not self.life_cycle.is_running():
                self.payments_queue.put([self.create_exit_payment()])
                break

    def create_calculations_report(self, payment_cycle, payment_logs, report_file_path, total_rewards):
        with open(report_file_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            # write headers and total rewards
            writer.writerow(["address", "type", "ratio", "reward", "fee_rate", "payment", "fee"])
            writer.writerow([self.baking_address, "B", 1.0, total_rewards, 0, total_rewards, 0])

            for pymnt_log in payment_logs:
                if pymnt_log.skipped:
                    continue

                # write row to csv file
                writer.writerow([pymnt_log.address, pymnt_log.type,
                                 "{0:f}".format(pymnt_log.ratio),
                                 "{0:f}".format(pymnt_log.service_fee_amount+pymnt_log.amount),
                                 "{0:f}".format(pymnt_log.service_fee_rate),
                                 "{0:f}".format(pymnt_log.amount),
                                 "{0:f}".format(pymnt_log.service_fee_amount)])

                logger.info("Reward created for cycle %s address %s amount %f fee %f tz type %s",
                            payment_cycle, pymnt_log.address, pymnt_log.amount, pymnt_log.service_fee_rate,
                            pymnt_log.type)

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
            while self.payments_queue.full():
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
                self.payments_queue.put(batch)

                # 2.5 rename payments/failed/csv_report.csv to payments/failed/csv_report.csv.BUSY
                # mark the files as in use. we do not want it to be read again
                # BUSY file will be removed, if successful payment is done
                os.rename(payment_failed_report_file, payment_failed_report_file + BUSY_FILE)
