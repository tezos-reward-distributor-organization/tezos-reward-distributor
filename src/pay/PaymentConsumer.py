import csv
import os
import threading
from random import randint
from time import sleep

from Constants import EXIT_PAYMENT_TYPE
from emails.email_manager import EmailManager
from pay.batch_payer import BatchPayer
from pay.regular_payer import RegularPayer
from util.dir_utils import payment_file_name, payment_report_name
from log_config import main_logger

logger = main_logger


class PaymentConsumer(threading.Thread):
    def __init__(self, name, payments_dir, key_name, client_path, payments_queue, node_addr, verbose=None,
                 dry_run=None):
        super(PaymentConsumer, self).__init__()

        self.name = name
        self.payments_dir = payments_dir
        self.key_name = key_name
        self.client_path = client_path
        self.payments_queue = payments_queue
        self.node_addr = node_addr
        self.verbose = verbose
        self.dry_run = dry_run
        self.mm = EmailManager()

        logger.debug('Consumer "%s" created', self.name)

        return

    def run(self):
        while True:
            try:
                # wait until a reward is present
                payment_items = self.payments_queue.get(True)

                if payment_items[0]["type"] == EXIT_PAYMENT_TYPE:
                    logger.debug("Exit signal received. Killing the thread...")
                    break

                if len(payment_items) == 1:
                    regular_payer = RegularPayer(self.client_path, self.key_name)
                    payment_log = regular_payer.pay(payment_items[0], self.verbose, dry_run=self.dry_run)
                    payment_logs = [payment_log]
                else:
                    batch_payer = BatchPayer(self.node_addr, self.client_path, self.key_name)
                    payment_logs = batch_payer.pay(payment_items, self.verbose, dry_run=self.dry_run)

                nb_failed = 0
                for pymnt_itm in payment_logs:
                    pymnt_cycle = pymnt_itm["cycle"]
                    pymnt_addr = pymnt_itm["address"]
                    pymnt_amnt = pymnt_itm["payment"]
                    pymnt_type = pymnt_itm["type"]
                    status = pymnt_itm["paid"]
                    hash = pymnt_itm["hash"]

                    if status:
                        pymt_log = payment_file_name(self.payments_dir, str(pymnt_cycle), pymnt_addr, pymnt_type)

                        # check and create required directories
                        if not os.path.exists(os.path.dirname(pymt_log)):
                            os.makedirs(os.path.dirname(pymt_log))

                        # create empty payment log file
                        with open(pymt_log, 'w') as f:
                            f.write('')

                        logger.info("Reward paid for cycle %s address %s amount %f tz", pymnt_cycle, pymnt_addr,
                                    pymnt_amnt)
                    else:
                        nb_failed = nb_failed + 1
                        logger.warning("NO Reward paid for cycle %s address %s amount %f tz: Reason client failed!",
                                       pymnt_cycle, pymnt_addr, pymnt_amnt)

                #
                #create report file and send email
                report_file = payment_report_name(self.payments_dir, str(pymnt_cycle),
                                                  "success" if nb_failed == 0 else 'failed_' + str(nb_failed))
                with open(report_file, "w") as f:
                    csvwriter = csv.writer(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                    csvwriter.writerow(["address", "type", "payment", "hash", "paid"])

                    for payment_item in payment_logs:
                        address = payment_item["address"]
                        type = payment_item["type"]
                        payment = payment_item["payment"]
                        hash = payment_item["hash"]
                        paid = payment_item["paid"]

                        # write row to csv file
                        csvwriter.writerow([address, type, "{0:f}".format(payment), hash, "1" if paid else "0"])

                self.mm.send_payment_mail(pymnt_cycle, report_file)
            except Exception as e:
                logger.error("Error at reward payment", e)

        logger.info("Consumer returning ...")

        return
