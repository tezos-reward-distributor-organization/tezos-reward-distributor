import os
from os import listdir
from os.path import join
from time import sleep
from Constants import PaymentStatus
from log_config import main_logger
from pay.payment_batch import PaymentBatch
from util.csv_payment_file_parser import CsvPaymentFileParser
from util.dir_utils import get_failed_payments_dir, PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR, remove_busy_file, BUSY_FILE

logger = main_logger.getChild("payment_producer")


class RetryProducer:
    def __init__(self, payments_queue, reward_api, payment_producer, payments_dir, initial_payment_cycle, retry_injected=False):
        self.payments_queue = payments_queue
        self.reward_api = reward_api
        self.payment_producer = payment_producer
        self.payments_root = payments_dir
        self.retry_injected = retry_injected
        self.initial_payment_cycle = initial_payment_cycle

    def retry_failed_payments(self):
        logger.debug("retry_failed_payments started")

        # 1 - list csv files under payments/failed directory
        # absolute path of csv files found under payments_root/failed directory
        failed_payments_dir = get_failed_payments_dir(self.payments_root)
        payment_reports_failed = [join(failed_payments_dir, x) for x in listdir(failed_payments_dir) if x.endswith('.csv')
                                  and int(x.split(".csv")[0]) >= self.initial_payment_cycle]

        if payment_reports_failed:
            payment_reports_failed = sorted(payment_reports_failed, key=self.get_basename)
            logger.debug("Failed payment files found are: '{}'".format(",".join(payment_reports_failed)))
        else:
            logger.info("No failed payment files found under directory '{}' on or after cycle '{}'".format(failed_payments_dir, self.initial_payment_cycle))

        # 2- for each csv file with name csv_report.csv
        for payment_failed_report_file in payment_reports_failed:
            logger.info("Working on failed payment file {}".format(payment_failed_report_file))

            # 2.1 - if there is a file csv_report.csv under payments/done, it means payment is already done
            if os.path.isfile(payment_failed_report_file.replace(PAYMENT_FAILED_DIR, PAYMENT_DONE_DIR)):
                # remove payments/failed/csv_report.csv
                os.remove(payment_failed_report_file)

                logger.info("Payment for failed payment {} is already done. Removing.".format(payment_failed_report_file))

                # remove payments/failed/csv_report.csv.BUSY
                # if there is a busy failed payment report file, remove it.
                remove_busy_file(payment_failed_report_file)

                # do not double pay
                continue

            # 2.2 - if queue is full, wait for sometime
            # make sure the queue is not full
            while self.payments_queue.full():
                logger.debug("Payments queue is full. Please wait three minutes.")
                sleep(60 * 3)

            cycle = int(os.path.splitext(os.path.basename(payment_failed_report_file))[0])

            # 2.3 read payments/failed/csv_report.csv file into a list of dictionaries
            batch = CsvPaymentFileParser().parse(payment_failed_report_file, cycle)

            nb_paid = len(list(filter(lambda f: f.paid == PaymentStatus.PAID, batch)))
            nb_done = len(list(filter(lambda f: f.paid == PaymentStatus.DONE, batch)))
            nb_injected = len(list(filter(lambda f: f.paid == PaymentStatus.INJECTED, batch)))
            nb_failed = len(list(filter(lambda f: f.paid == PaymentStatus.FAIL, batch)))

            logger.info("Summary {} paid, {} done, {} injected, {} fail".format(nb_paid, nb_done, nb_injected, nb_failed))

            if self.retry_injected:
                self.convert_injected_to_fail(batch)

            # 2.5 - Need to fetch current balance for addresses of any failed payments
            self.reward_api.update_current_balances(batch)

            # 2.6 - put records into payment_queue. payment_consumer will make payments
            self.payments_queue.put(PaymentBatch(self.payment_producer, cycle, batch))

            # 2.7 - rename payments/failed/csv_report.csv to payments/failed/csv_report.csv.BUSY
            # mark the files as in use. we do not want it to be read again
            # BUSY file will be removed, if successful payment is done
            os.rename(payment_failed_report_file, payment_failed_report_file + BUSY_FILE)

        return

    @staticmethod
    def convert_injected_to_fail(batch):
        nb_converted = 0
        for pl in batch:
            if pl.paid == PaymentStatus.INJECTED:
                pl.paid = PaymentStatus.FAIL
                nb_converted += 1
                logger.debug("Reward converted from %s to fail for cycle %s, address %s, amount %f, tz type %s", pl.paid, pl.cycle, pl.address, pl.amount, pl.type)

        if nb_converted:
            logger.info("{} rewards converted from injected to fail.".format(nb_converted))

    @staticmethod
    def get_basename(x):
        return int(os.path.splitext(os.path.basename(x))[0])
