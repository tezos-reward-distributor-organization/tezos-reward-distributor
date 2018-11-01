import os
import subprocess
import threading

from Constants import EXIT_PAYMENT_TYPE
from util.dir_utils import payment_file_name
from log_config import main_logger

logger = main_logger


class RegularClientPaymentConsumer(threading.Thread):
    def __init__(self, name, payments_dir, key_name, transfer_command, payments_queue):
        super(RegularClientPaymentConsumer, self).__init__()

        self.name = name
        self.payments_dir = payments_dir
        self.key_name = key_name
        self.transfer_command = transfer_command
        self.payments_queue = payments_queue

        logger.debug('Consumer "%s" created', self.name)

        return

    def run(self):
        while True:
            try:
                # wait until a reward is present
                payment_item = self.payments_queue.get(True)

                pymnt_addr = payment_item["address"]
                pymnt_amnt = payment_item["payment"]
                pymnt_cycle = payment_item["cycle"]
                type = payment_item["type"]

                if type == EXIT_PAYMENT_TYPE:
                    logger.debug("Exit signal received. Killing the thread...")
                    break

                if pymnt_amnt > 0:
                    cmd = self.transfer_command.format(pymnt_amnt, self.key_name, pymnt_addr)

                    logger.debug("Reward payment attempt for cycle %s address %s amount %f tz type %s", pymnt_cycle,
                                 pymnt_addr, pymnt_amnt, type)

                    logger.debug("Reward payment command '{}'".format(cmd))

                    # execute client
                    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    process.wait()
                    return_code = process.returncode
                else:
                    logger.debug("Reward payment command not executed for %s because reward is 0", pymnt_addr)
                    return_code = 0

                if return_code == 0:
                    pymt_log = payment_file_name(self.payments_dir, str(pymnt_cycle), pymnt_addr, type)

                    # check and create required directories
                    if not os.path.exists(os.path.dirname(pymt_log)):
                        os.makedirs(os.path.dirname(pymt_log))

                    # create empty payment log file
                    with open(pymt_log, 'w') as f:
                        f.write('')

                    logger.info("Reward paid for cycle %s address %s amount %f tz", pymnt_cycle, pymnt_addr, pymnt_amnt)
                else:
                    logger.warning("Reward NOT paid for cycle %s address %s amount %f tz: Reason client failed!",
                                   pymnt_cycle, pymnt_addr, pymnt_amnt)
            except Exception as e:
                logger.error("Error at reward payment", e)

        logger.info("Consumer returning ...")

        return
