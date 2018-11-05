import os
import threading
from random import randint
from time import sleep

from Constants import EXIT_PAYMENT_TYPE
from pay.batch_payer import BatchPayer
from pay.regular_payer import RegularPayer
from util.dir_utils import payment_file_name
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
                    return_code = regular_payer.pay(payment_items[0], self.verbose, dry_run=self.dry_run)
                else:
                    batch_payer = BatchPayer(self.node_addr, self.client_path, self.key_name)
                    return_code = False
                    max_try=3
                    for attempt in range(max_try):
                        return_code = batch_payer.pay(payment_items, self.verbose, dry_run=self.dry_run)
                        if return_code: break
                        logger.debug("Batch payment attempt {} failed".format(attempt))
                        if attempt > max_try:
                            slp_tm = randint(10, 50)
                            logger.debug("Wait for {} seconds before trying again".format(slp_tm))
                            sleep(slp_tm)

                for pymnt_itm in payment_items:
                    pymnt_cycle = pymnt_itm["cycle"]
                    pymnt_addr = pymnt_itm["address"]
                    pymnt_amnt = pymnt_itm["payment"]
                    pymnt_type = pymnt_itm["type"]

                    if return_code:
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
                        logger.warning("Reward NOT paid for cycle %s address %s amount %f tz: Reason client failed!",
                                       pymnt_cycle, pymnt_addr, pymnt_amnt)
            except Exception as e:
                logger.error("Error at reward payment", e)

        logger.info("Consumer returning ...")

        return
