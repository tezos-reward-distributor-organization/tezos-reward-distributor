import csv
import functools
import threading
import os
import time

from Constants import EXIT_PAYMENT_TYPE
from calc.calculate_phase5 import CalculatePhase5
from calc.calculate_phase6 import CalculatePhase6
from emails.email_manager import EmailManager
from log_config import main_logger
from model.reward_log import cmp_by_type_balance
from pay.batch_payer import BatchPayer
from util.dir_utils import payment_report_file_path, get_busy_file

logger = main_logger
MUTEZ = 1e6


def count_and_log_failed(payment_logs, pymnt_cycle):
    nb_failed = 0
    for pymnt_itm in payment_logs:
        if pymnt_itm.paid:
            logger.info("Reward paid for cycle %s address %s amount %f tz type %s",
                        pymnt_cycle, pymnt_itm.address, pymnt_itm.amount, pymnt_itm.type)
        else:
            nb_failed = nb_failed + 1
            logger.warning("No Reward paid for cycle %s address %s amount %f tz: Reason client failed!",
                           pymnt_cycle, pymnt_itm.address, pymnt_itm.amount)
    return nb_failed


class PaymentConsumer(threading.Thread):
    def __init__(self, name, payments_dir, key_name, client_path, payments_queue, node_addr, wllt_clnt_mngr,
                 verbose=None, dry_run=None, delegator_pays_xfer_fee=True, dest_map=None):
        super(PaymentConsumer, self).__init__()

        self.dest_map = dest_map if dest_map else {}
        self.name = name
        self.payments_dir = payments_dir
        self.key_name = key_name
        self.client_path = client_path
        self.payments_queue = payments_queue
        self.node_addr = node_addr
        self.verbose = verbose
        self.dry_run = dry_run
        self.mm = EmailManager()
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.delegator_pays_xfer_fee = delegator_pays_xfer_fee

        logger.debug('Consumer "%s" created', self.name)

        return

    def run(self):
        while True:
            try:
                # 1-  wait until a reward is present
                payment_items = self.payments_queue.get(True)

                if payment_items[0].type == EXIT_PAYMENT_TYPE:
                    logger.debug("Exit signal received. Killing the thread...")
                    break

                # each log in the batch belongs to the same cycle
                pymnt_cycle = payment_items[0].cycle

                time.sleep(1)

                logger.info("Starting payments for cycle {}".format(pymnt_cycle))

                # 2- select suitable payment script
                # if len(payment_items) == 1:
                # regular_payer = RegularPayer(self.client_path, self.key_name)
                # payment_log = regular_payer.pay(payment_items[0], self.verbose, dry_run=self.dry_run)
                # payment_logs = [payment_log]

                phase5 = CalculatePhase5(self.dest_map)
                payment_items, _ = phase5.calculate(payment_items, None)

                phase6 = CalculatePhase6(addr_dest_dict=self.dest_map)
                payment_items, _ = phase6.calculate(payment_items, None)

                payment_items.sort(key=functools.cmp_to_key(cmp_by_type_balance))

                batch_payer = BatchPayer(self.node_addr, self.key_name, self.wllt_clnt_mngr,
                                         self.delegator_pays_xfer_fee)

                # 3- do the payment
                payment_logs = batch_payer.pay(payment_items, self.verbose, dry_run=self.dry_run)

                # 4- count failed payments
                nb_failed = count_and_log_failed(payment_logs, pymnt_cycle)

                # 5- create payment report file
                report_file = self.create_payment_report(nb_failed, payment_logs, pymnt_cycle)

                # 6- upon successful payment, clean failure reports
                # note that failed payment reports are cleaned after creation of successful payment report
                if nb_failed == 0: self.clean_failed_payment_reports(pymnt_cycle)

                # 7- send email
                if not self.dry_run:
                    self.mm.send_payment_mail(pymnt_cycle, report_file, nb_failed)

            except Exception:
                logger.error("Error at reward payment", exc_info=True)

        logger.info("Consumer returning ...")

        return

    def clean_failed_payment_reports(self, payment_cycle):
        # 1- generate path of a assumed failure report file
        # if it exists, remove it
        failure_report_file = payment_report_file_path(self.payments_dir, payment_cycle, 1)
        if os.path.isfile(failure_report_file):
            os.remove(failure_report_file)
        # 2- generate path of a assumed busy failure report file
        # if it exists, remove it
        failure_report_busy_file = get_busy_file(failure_report_file)
        if os.path.isfile(failure_report_busy_file):
            os.remove(failure_report_busy_file)

    #
    # create report file
    def create_payment_report(self, nb_failed, payment_logs, payment_cycle):
        report_file = payment_report_file_path(self.payments_dir, payment_cycle, nb_failed)
        with open(report_file, "w") as f:
            csv_writer = csv.writer(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["address", "type", "payment", "hash", "paid"])

            for pl in payment_logs:
                # write row to csv file
                csv_writer.writerow(
                    [pl.address, pl.type, "{0:f}".format(pl.amount/ MUTEZ), pl.hash,
                     "1" if pl.paid else "0"])

                logger.info("Payment done for address %s type %s balance {:>10.2f} ratio {:.2f} fee_ratio {:.2f} amount {:>8.2f} fee_amount {:.2f} fee_rate {:.2f}, skipped %s atphase %s desc %s "
                    .format(pl.balance / MUTEZ, pl.ratio, pl.service_fee_ratio, pl.amount / MUTEZ,
                            pl.service_fee_amount / MUTEZ, pl.service_fee_rate), pl.address, pl.type, pl.skipped, pl.skippedatphase, pl.desc)

        return report_file
