import _thread
import csv
import os
import threading
import time

from time import sleep
from Constants import RunMode
from log_config import main_logger
from model.reward_log import RewardLog
from model.rules_model import RulesModel
from exception.tzscan import TzScanException
from requests import ReadTimeout, ConnectTimeout
from pay.double_payment_check import check_past_payment
from pay.payment_batch import PaymentBatch
from pay.payment_producer_abc import PaymentProducerABC
from util.csv_payment_file_parser import CsvPaymentFileParser
from calc.phased_payment_calculator import PhasedPaymentCalculator
from util.dir_utils import get_calculation_report_file, get_failed_payments_dir, PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR, \
    remove_busy_file, BUSY_FILE

logger = main_logger

MUTEZ = 1e+6


class PaymentProducer(threading.Thread, PaymentProducerABC):
    def __init__(self, name, initial_payment_cycle, network_config, payments_dir, calculations_dir, run_mode,
                 service_fee_calc, release_override, payment_offset, baking_cfg, payments_queue, life_cycle,
                 dry_run, wllt_clnt_mngr, node_url, provider_factory, verbose=False):
        super(PaymentProducer, self).__init__()
        self.rules_model = RulesModel(baking_cfg.get_excluded_set_tob(), baking_cfg.get_excluded_set_toe(),
                                      baking_cfg.get_excluded_set_tof(), baking_cfg.get_dest_map())
        self.baking_address = baking_cfg.get_baking_address()
        self.owners_map = baking_cfg.get_owners_map()
        self.founders_map = baking_cfg.get_founders_map()
        self.min_delegation_amt_in_mutez = baking_cfg.get_min_delegation_amount() * MUTEZ
        self.pymnt_scale = baking_cfg.get_payment_scale()
        self.prcnt_scale = baking_cfg.get_percentage_scale()
        self.delegator_pays_xfer_fee = baking_cfg.get_delegator_pays_xfer_fee()

        self.name = name

        self.reward_api = provider_factory.newRewardApi(network_config, self.baking_address, wllt_clnt_mngr, node_url)
        self.block_api = provider_factory.newBlockApi(network_config, wllt_clnt_mngr, node_url)

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

        self.payment_calc = PhasedPaymentCalculator(self.founders_map, self.owners_map, self.fee_calc,
                                                    self.min_delegation_amt_in_mutez, self.rules_model)

        self.retry_fail_thread = threading.Thread(target=self.retry_fail_run, name=self.name + "_retry_fail")
        self.retry_fail_event = threading.Event()

        logger.info('Producer "{}" started'.format(self.name))

    def exit(self):
        if not self.exiting:
            self.payments_queue.put(PaymentBatch(self, 0, [self.create_exit_payment()]))
            self.exiting = True

            if self.life_cycle.is_running() and threading.current_thread() is not threading.main_thread():
                _thread.interrupt_main()

            if self.retry_fail_event:
                self.retry_fail_event.set()

    def retry_fail_run(self):
        logger.info('Retry Fail thread "{}" started'.format(self.retry_fail_thread.name))

        sleep(60)  # producer thread already tried once, wait for next try

        while not self.exiting and self.life_cycle.is_running():
            self.retry_failed_payments()

            try:
                # prepare to wait on event
                self.retry_fail_event.clear()

                # this will either return with timeout or set from parent producer thread
                self.retry_fail_event.wait(60 * 60)  # 1 hour
            except RuntimeError:
                pass

        pass

    def run(self):
        # call first retry if not in onetime mode.
        # retry_failed script is more suitable for one time cases.
        if not self.run_mode == RunMode.ONETIME:
            self.retry_failed_payments()

        # first retry is done by producer thread, start retry thread for further retries
        if self.run_mode == RunMode.FOREVER:
            self.retry_fail_thread.start()

        crrnt_cycle = self.block_api.get_current_cycle()
        pymnt_cycle = self.initial_payment_cycle

        # if non-positive initial_payment_cycle, set initial_payment_cycle to
        # 'current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1)'
        if self.initial_payment_cycle <= 0:
            pymnt_cycle = crrnt_cycle - abs(self.initial_payment_cycle) - (self.nw_config['NB_FREEZE_CYCLE'] + 1)
            logger.debug("Payment cycle is set to {}".format(pymnt_cycle))

        while not self.exiting and self.life_cycle.is_running():

            # take a breath
            time.sleep(5)

            try:
                current_level = self.block_api.get_current_level(verbose=self.verbose)
                crrnt_cycle = self.block_api.level_to_cycle(current_level)

                # create reports dir
                if self.calculations_dir and not os.path.exists(self.calculations_dir):
                    os.makedirs(self.calculations_dir)

                logger.debug("Checking for pending payments : payment_cycle <= "
                             "current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override")
                logger.info("Checking for pending payments : checking {} <= {} - ({} + 1) - {}".
                            format(pymnt_cycle, crrnt_cycle, self.nw_config['NB_FREEZE_CYCLE'],
                                   self.release_override))

                # payments should not pass beyond last released reward cycle
                if pymnt_cycle <= crrnt_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override:
                    if not self.payments_queue.full():

                        result = self.try_to_pay(pymnt_cycle)

                        if result:
                            # single run is done. Do not continue.
                            if self.run_mode == RunMode.ONETIME:
                                logger.info("Run mode ONETIME satisfied. Killing the thread ...")
                                self.exit()
                                break
                            else:
                                pymnt_cycle = pymnt_cycle + 1

                    # end of queue size check
                    else:
                        logger.debug("Wait a few minutes, queue is full")
                        # wait a few minutes to let payments done
                        time.sleep(60 * 3)
                # end of payment cycle check
                else:
                    logger.info("No pending payments for cycle {},current cycle is {}".format(pymnt_cycle, crrnt_cycle))

                    # pending payments done. Do not wait any more.
                    if self.run_mode == RunMode.PENDING:
                        logger.info("Run mode PENDING satisfied. Killing the thread ...")
                        self.exit()
                        break

                    time.sleep(10)

                    # calculate number of blocks until end of current cycle
                    nb_blocks_remaining = (crrnt_cycle + 1) * self.nw_config['BLOCKS_PER_CYCLE'] - current_level
                    # plus offset. cycle beginnings may be busy, move payments forward
                    nb_blocks_remaining = nb_blocks_remaining + self.payment_offset

                    logger.debug("Wait until next cycle, for {} blocks".format(nb_blocks_remaining))

                    # wait until current cycle ends
                    self.wait_until_next_cycle(nb_blocks_remaining)

            except TzScanException:
                logger.warn("Tzscan error at reward loop", exc_info=True)
            except Exception:
                logger.error("Error at payment producer loop", exc_info=True)

        # end of endless loop
        logger.info("Producer returning ...")

        # ensure consumer exits
        self.exit()

        return

    def try_to_pay(self, pymnt_cycle):
        try:
            logger.info("Payment cycle is " + str(pymnt_cycle))

            # 0- check for past payment evidence for current cycle
            past_payment_state = check_past_payment(self.payments_root, pymnt_cycle)

            if not self.dry_run and past_payment_state:
                logger.warn(past_payment_state)
                return True

            # 1- get reward data
            reward_model = self.reward_api.get_rewards_for_cycle_map(pymnt_cycle, verbose=self.verbose)
            # 2- calculate rewards
            reward_logs, total_amount = self.payment_calc.calculate(reward_model)
            # set cycle info
            for rl in reward_logs: rl.cycle = pymnt_cycle
            total_amount_to_pay = sum([rl.amount for rl in reward_logs if rl.payable])

            # 4- if total_rewards > 0, proceed with payment
            if total_amount_to_pay > 0:
                report_file_path = get_calculation_report_file(self.calculations_dir, pymnt_cycle)

                # 5- send to payment consumer
                self.payments_queue.put(PaymentBatch(self, pymnt_cycle, reward_logs))
                # logger.info("Total payment amount is {:,} mutez. %s".format(total_amount_to_pay),
                #            "" if self.delegator_pays_xfer_fee else "(Transfer fee is not included)")

                logger.debug("Creating calculation report (%s)", report_file_path)

                # 6- create calculations report file. This file contains calculations details
                self.create_calculations_report(reward_logs, report_file_path, total_amount)
                # 7- next cycle
                # processing of cycle is done
                logger.info("Reward creation is done for cycle {}, {} payments.".format(pymnt_cycle, len(reward_logs)))

            elif total_amount_to_pay == 0:
                logger.info("Total payment amount is 0. Nothing to pay!")

            return True
        except ReadTimeout:
            logger.warn("Tzscan call failed", exc_info=True)
            return False
        except ConnectTimeout:
            logger.warn("Tzscan connection failed", exc_info=True)
            return False
        except TzScanException:
            logger.warn("Tzscan error at reward loop", exc_info=True)
            return False
        except Exception:
            logger.error("Error at payment producer loop", exc_info=True)
            return False
        finally:
            sleep(10)

    def wait_until_next_cycle(self, nb_blocks_remaining):
        for x in range(nb_blocks_remaining):
            time.sleep(self.nw_config['BLOCK_TIME_IN_SEC'])

            # if shutting down, exit
            if not self.life_cycle.is_running():
                self.exit()
                break

    def create_calculations_report(self, payment_logs, report_file_path, total_rewards):
        with open(report_file_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            # write headers and total rewards
            writer.writerow(
                ["address", "type", "balance", "ratio", "fee_ratio", "amount", "fee_amount", "fee_rate", "payable",
                 "skipped", "atphase", "desc"])

            writer.writerow([self.baking_address, "B", sum([pl.balance for pl in payment_logs]),
                             "{0:f}".format(1.0),
                             "{0:f}".format(0.0),
                             "{0:f}".format(total_rewards),
                             "{0:f}".format(0.0),
                             "{0:f}".format(0.0),
                             "0", "0", "-1", "Baker"
                             ])

            for pymnt_log in payment_logs:
                # write row to csv file
                writer.writerow([pymnt_log.address, pymnt_log.type, pymnt_log.balance,
                                 "{0:.10f}".format(pymnt_log.ratio),
                                 "{0:.10f}".format(pymnt_log.service_fee_ratio),
                                 "{0:f}".format(pymnt_log.amount),
                                 "{0:f}".format(pymnt_log.service_fee_amount),
                                 "{0:f}".format(pymnt_log.service_fee_rate),
                                 "1" if pymnt_log.payable else "0", "1" if pymnt_log.skipped else "0",
                                 pymnt_log.skippedatphase if pymnt_log.skipped else "-1",
                                 pymnt_log.desc if pymnt_log.desc else "None"
                                 ])

                logger.debug("Reward created for address %s type %s balance {:>10.2f} ratio {:.8f} fee_ratio {:.6f} "
                             "amount {:>8.2f} fee_amount {:.2f} fee_rate {:.2f} payable %s skipped %s atphase %s desc %s"
                             .format(pymnt_log.balance / MUTEZ, pymnt_log.ratio, pymnt_log.service_fee_ratio,
                                     pymnt_log.amount / MUTEZ, pymnt_log.service_fee_amount / MUTEZ,
                                     pymnt_log.service_fee_rate), pymnt_log.address, pymnt_log.type, pymnt_log.payable,
                             pymnt_log.skipped, pymnt_log.skippedatphase, pymnt_log.desc)

    @staticmethod
    def create_exit_payment():
        return RewardLog.ExitInstance()

    def retry_failed_payments(self):
        logger.debug("retry_failed_payments started")

        # 1 - list csv files under payments/failed directory
        # absolute path of csv files found under payments_root/failed directory
        failed_payments_dir = get_failed_payments_dir(self.payments_root)
        payment_reports_failed = [os.path.join(failed_payments_dir, x) for x in
                                  os.listdir(failed_payments_dir) if x.endswith('.csv')]

        if payment_reports_failed:
            logger.debug("Failed payment files found are: '{}'".format(",".join(payment_reports_failed)))
        else:
            logger.debug("No failed payment files found under directory '{}'".format(failed_payments_dir))

        # 2- for each csv file with name csv_report.csv
        for payment_failed_report_file in payment_reports_failed:
            logger.info("Working on failed payment file {}".format(payment_failed_report_file))

            # 2.1 - if there is a file csv_report.csv under payments/done, it means payment is already done
            if os.path.isfile(payment_failed_report_file.replace(PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR)):
                # remove payments/failed/csv_report.csv
                os.remove(payment_failed_report_file)
                logger.info(
                    "Payment for failed payment {} is already done. Removing.".format(payment_failed_report_file))

                # remove payments/failed/csv_report.csv.BUSY
                # if there is a busy failed payment report file, remove it.
                remove_busy_file(payment_failed_report_file)

                # do not double pay
                continue

            # 2.2 - if queue is full, wait for sometime
            # make sure the queue is not full
            while self.payments_queue.full():
                logger.debug("Payments queue is full. Wait a few minutes.")
                time.sleep(60 * 3)

            cycle = int(os.path.splitext(os.path.basename(payment_failed_report_file))[0])

            # 2.3 read payments/failed/csv_report.csv file into a list of dictionaries
            batch = CsvPaymentFileParser().parse(payment_failed_report_file, cycle)

            # 2.4 put records into payment_queue. payment_consumer will make payments
            self.payments_queue.put(PaymentBatch(self, cycle, batch))

            # 2.5 rename payments/failed/csv_report.csv to payments/failed/csv_report.csv.BUSY
            # mark the files as in use. we do not want it to be read again
            # BUSY file will be removed, if successful payment is done
            os.rename(payment_failed_report_file, payment_failed_report_file + BUSY_FILE)

    def notify_retry_fail_thread(self):
        self.retry_fail_event.set()

    # upon success retry failed payments if present
    # success may indicate what went wrong in past is fixed.
    def on_success(self, pymnt_batch):
        self.notify_retry_fail_thread()

    def on_fail(self, pymnt_batch):
        pass
