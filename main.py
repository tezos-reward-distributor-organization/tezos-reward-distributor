import os
import queue
import subprocess
import threading
import time

from BussinessConfiguration import founders_map, BAKING_ADDRESS, supporters_set, specials_map, STANDARD_FEE, owners_map
from NetworkConfiguration import network_config_map
from PaymentCalculator import PaymentCalculator
from ServiceFeeCalculator import ServiceFeeCalculator
from TzScanBlockApi import TzScanBlockApi
from TzScanRewardApi import TzScanRewardApi
from TzScanRewardCalculator import TzScanRewardCalculator
from logconfig import main_logger

BUF_SIZE = 50
NW = network_config_map['ZERONET']
keyname = 'zeronetme2'

# execution parameters, possible to move to command line parameters
NB_CONSUMERS = 1
COMM_TRANSFER = "~/zeronet.sh client transfer {} from {} to {} --fee 0"
MAX_DEPTH = 2
PAYMNETS_DIR = os.path.expanduser("./payments/")

payments_queue = queue.Queue(BUF_SIZE)

logger = main_logger


class ProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name
        self.block_api = TzScanBlockApi(NW)
        self.fee_calc = ServiceFeeCalculator(supporters_set, specials_map, STANDARD_FEE)
        logger.debug('Producer started')

    def run(self):
        current_cycle = self.block_api.get_current_cycle()
        initial_payment_cycle = current_cycle - MAX_DEPTH - (NW['NB_FREEZE_CYCLE'] + 1)
        payment_cycle = initial_payment_cycle

        while True:

            # take a breath
            time.sleep(10)

            current_level = self.block_api.get_current_level()
            current_cycle = self.block_api.level_to_cycle(current_level)

            # payments should not pass beyond last released reward cycle
            if payment_cycle <= current_cycle - (NW['NB_FREEZE_CYCLE'] + 1):
                if not payments_queue.full():
                    try:

                        logger.info("Payment cycle is " + str(payment_cycle))

                        reward_api = TzScanRewardApi(NW, BAKING_ADDRESS)
                        reward_data = reward_api.get_rewards_for_cycle_map(payment_cycle)
                        reward_calc = TzScanRewardCalculator(founders_map, reward_data)
                        rewards = reward_calc.calculate()
                        total_rewards = reward_calc.get_total_rewards()

                        logger.info("Total rewards=" + str(total_rewards))

                        payment_calc = PaymentCalculator(founders_map, owners_map, rewards, total_rewards,
                                                         self.fee_calc, payment_cycle)
                        payments = payment_calc.calculate()
                        for payment_item in payments:
                            address = payment_item["address"]
                            payment = payment_item["payment"]
                            fee = payment_item["fee"]
                            type = payment_item["type"]

                            pymt_log = payment_file_name(PAYMNETS_DIR, str(payment_cycle), address, type)

                            if os.path.isfile(pymt_log):
                                logger.warning(
                                    "Reward not created for cycle %s address %s amount %f tz %s: Reason payment log already present",
                                    payment_cycle, address, payment,type)
                            else:
                                payments_queue.put(payment_item)
                                logger.info("Reward created for cycle %s address %s amount %f fee %f tz type %s",
                                            payment_cycle, address, payment, fee, type)

                        # processing of cycle is done
                        logger.info("Reward creation done for cycle %s", payment_cycle)
                        payment_cycle = payment_cycle + 1

                    except Exception as e:
                        logger.error("Error at reward calculation", e)

                # end of queue size check
                else:
                    logger.debug("Wait a few minutes, queue is full")
                    # wait a few minutes to let payments done
                    time.sleep(60 * 3)
            # end of payment cycle check
            else:
                nb_blocks_remaining = (current_cycle + 1) * NW['BLOCKS_PER_CYCLE'] - current_level

                logger.debug("Wait until next cycle, for {} blocks".format(nb_blocks_remaining))

                # wait until current cycle ends
                time.sleep(nb_blocks_remaining * NW['BLOCK_TIME_IN_SEC'])

        # end of endless loop
        return


class ConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(ConsumerThread, self).__init__()
        self.target = target
        self.name = name
        logger.debug('Consumer "%s" created', self.name)
        return

    def run(self):
        while True:
            try:
                # wait until a reward is present
                payment_item = payments_queue.get(True)

                pymnt_addr = payment_item["address"]
                pymnt_amnt = payment_item["payment"]
                pymnt_cycle = payment_item["cycle"]
                type = payment_item["type"]

                cmd = COMM_TRANSFER.format(pymnt_amnt, keyname, pymnt_addr)

                logger.debug("Reward payment attempt for cycle %s address %s amount %f tz", pymnt_cycle, pymnt_addr,
                             pymnt_amnt)

                # execute client
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                process.wait()

                if process.returncode == 0:
                    pymt_log = payment_file_name(PAYMNETS_DIR, str(pymnt_cycle), pymnt_addr, type)

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

        return


def payment_file_name(pymnt_dir, pymnt_cycle, pymnt_addr, pymnt_type):
    return pymnt_dir + "/" + pymnt_cycle + "/" + pymnt_addr + '_' + pymnt_type + '.txt'


if __name__ == '__main__':
    p = ProducerThread(name='producer')
    p.start()

    for i in range(NB_CONSUMERS):
        c = ConsumerThread(name='consumer' + str(i))
        time.sleep(1)
        c.start()
    time.sleep(2)
