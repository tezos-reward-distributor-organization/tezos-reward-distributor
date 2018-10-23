import argparse
import os
import queue
import subprocess
import threading
import time

from BussinessConfiguration import founders_map, BAKING_ADDRESS, supporters_set, specials_map, STANDARD_FEE, owners_map
from ClientConfiguration import COMM_TRANSFER
from NetworkConfiguration import network_config_map
from PaymentCalculator import PaymentCalculator
from ServiceFeeCalculator import ServiceFeeCalculator
from TzScanBlockApi import TzScanBlockApi
from TzScanRewardApi import TzScanRewardApi
from TzScanRewardCalculator import TzScanRewardCalculator
from logconfig import main_logger

# execution parameters, possible to move to command line parameters
NB_CONSUMERS = 1
BUF_SIZE = 50
payments_queue = queue.Queue(BUF_SIZE)
logger = main_logger


class ProducerThread(threading.Thread):
    def __init__(self, name, initial_payment_cycle, network_config, payments_dir):
        super(ProducerThread, self).__init__()
        self.name = name
        self.block_api = TzScanBlockApi(network_config)
        self.fee_calc = ServiceFeeCalculator(supporters_set, specials_map, STANDARD_FEE)
        self.initial_payment_cycle = initial_payment_cycle
        self.nw_config = network_config
        self.payments_dir = payments_dir

        logger.debug('Producer started')

    def run(self):
        current_cycle = self.block_api.get_current_cycle()

        payment_cycle = self.initial_payment_cycle

        # if non-positive initial_payment_cycle, set initial_payment_cycle to 'current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1)'
        if self.initial_payment_cycle <= 0:
            payment_cycle = current_cycle - abs(self.initial_payment_cycle) - (self.nw_config['NB_FREEZE_CYCLE'] + 1)

        while True:

            # take a breath
            time.sleep(10)

            current_level = self.block_api.get_current_level()
            current_cycle = self.block_api.level_to_cycle(current_level)

            # payments should not pass beyond last released reward cycle
            if payment_cycle <= current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1):
                if not payments_queue.full():
                    try:

                        logger.info("Payment cycle is " + str(payment_cycle))

                        reward_api = TzScanRewardApi(self.nw_config, BAKING_ADDRESS)
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

                            pymt_log = payment_file_name(self.payments_dir, str(payment_cycle), address, type)

                            if os.path.isfile(pymt_log):
                                logger.warning(
                                    "Reward not created for cycle %s address %s amount %f tz %s: Reason payment log already present",
                                    payment_cycle, address, payment, type)
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
                nb_blocks_remaining = (current_cycle + 1) * self.nw_config['BLOCKS_PER_CYCLE'] - current_level

                logger.debug("Wait until next cycle, for {} blocks".format(nb_blocks_remaining))

                # wait until current cycle ends
                time.sleep(nb_blocks_remaining * self.nw_config['BLOCK_TIME_IN_SEC'])

        # end of endless loop
        return


class ConsumerThread(threading.Thread):
    def __init__(self, name, payments_dir, key_name, transfer_command):
        super(ConsumerThread, self).__init__()

        self.name = name
        self.payments_dir = payments_dir
        self.key_name = key_name
        self.transfer_command = transfer_command

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

                cmd = self.transfer_command.format(pymnt_amnt, self.key_name, pymnt_addr)

                logger.debug("Reward payment attempt for cycle %s address %s amount %f tz", pymnt_cycle, pymnt_addr,
                             pymnt_amnt)

                # execute client
                process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                process.wait()

                if process.returncode == 0:
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

        return


def payment_file_name(pymnt_dir, pymnt_cycle, pymnt_addr, pymnt_type):
    return pymnt_dir + "/" + pymnt_cycle + "/" + pymnt_addr + '_' + pymnt_type + '.txt'


def main(args):
    network_config = network_config_map[args.network]
    key = args.key
    payments_dir = os.path.expanduser(args.payments_dir)

    p = ProducerThread(name='producer', initial_payment_cycle=args.initial_cycle, network_config=network_config,
                       payments_dir=payments_dir)
    p.start()

    for i in range(NB_CONSUMERS):
        c = ConsumerThread(name='consumer' + str(i), payments_dir=payments_dir, key_name=key,
                           transfer_command=COMM_TRANSFER.replace("%network%", network_config['NAME'].lower()))
        time.sleep(1)
        c.start()
    time.sleep(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("key", help="baker's tzaddress or correspoding key name")
    parser.add_argument("-N", "--network", help="network name", choices=['ZERONET', 'ALPHANET', 'MAINNET'],
                        default='MAINNET')
    parser.add_argument("-D", "--payments_dir", help="Directory to create payment logs", default='./payments')
    parser.add_argument("-C", "--initial_cycle",
                        help="First cycle to start payment. For last released rewards, set to 0. Non-positive values are interpreted as : current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1)",
                        type=int, default=0)

    args = parser.parse_args()

    logger.info("Tezos Reward Distributer is Starting")
    logger.info("Current network is {}".format(args.network))
    logger.info("Keyname {}".format(args.key))
    logger.info("--------------------------------------------")
    logger.info("Author huseyinabanox@gmail.com")
    logger.info("Please leave author information")
    logger.info("--------------------------------------------")

    main(args)
