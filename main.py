import threading
import queue
import time
from math import floor
import subprocess
import requests
import os
from logconfig import main_logger

BUF_SIZE = 50
ONE_MILLION = 1000000

# number of cycles network keeps rewards
NB_FREEZE_CYCLE = 5
# number of cycles before network releases rewards
CYCLE_PYMNT_OFFSET = NB_FREEZE_CYCLE + 1
# baker's 'tz' address, NOT A KT address
BAKING_ADDRESS = "tz1YZReTLamLhyPLGSALa4TbMhjjgnSi2cqP"

# execution parameters, possible to move to command line parameters
NB_CONSUMERS = 1
COMM_TRANSFER = "~/zeronet.sh client transfer {} from zeronetme2 to {} --fee 0"
MAX_DEPTH = 2
PAYMNETS_DIR = os.path.expanduser("~/payments/")

# network parameters
REWARDS_SPLIT_API_URL = 'http://zeronet-api.tzscan.io/v1/rewards_split/{}?cycle={}&p={}'
HEAD_API_URL = 'http://zeronet-api.tzscan.io/v2/head'
BLOCKS_PER_CYCLE = 128
BLOCK_TIME_IN_SEC = 60

payments_queue = queue.Queue(BUF_SIZE)

logger = main_logger

class ProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name

        logger.debug('Producer started')

    def run(self):
        current_cycle = self.get_current_cycle()
        initial_payment_cycle = current_cycle - MAX_DEPTH - CYCLE_PYMNT_OFFSET
        payment_cycle = initial_payment_cycle

        while True:

            # take a breath
            time.sleep(10)

            current_level = self.get_current_level()
            current_cycle = self.level_to_cycle(current_level)

            # payments should not pass beyond last released reward cycle
            if payment_cycle <= current_cycle - CYCLE_PYMNT_OFFSET:
                if not payments_queue.full():
                    try:

                        logger.info("Payment cycle is " + str(payment_cycle))
                        root = self.get_rewards_for_cycle_map(payment_cycle)

                        delegate_staking_balance = int(root["delegate_staking_balance"])
                        blocks_rewards = int(root["blocks_rewards"])
                        endorsements_rewards = int(root["endorsements_rewards"])
                        fees = int(root["fees"])
                        total_rewards = blocks_rewards + endorsements_rewards + fees

                        logger.info("Total rewards=" + str(total_rewards))

                        delegators_balance = root["delegators_balance"]
                        for dbalance in delegators_balance:
                            address = dbalance[0]["tz"]
                            balance = int(dbalance[1])
                            share_rate = balance / delegate_staking_balance
                            reward_share = round(total_rewards * share_rate / ONE_MILLION, 3)
                            reward_item = {"cycle": payment_cycle, "address": address, "reward": reward_share}

                            pymnt_addr = reward_item["address"]
                            pymt_log = PAYMNETS_DIR + "/" + str(payment_cycle) + "/" + pymnt_addr + '.txt'

                            if os.path.isfile(pymt_log):
                                logger.warning(
                                    "Reward not created for cycle %s address %s amount %f tz : Reason payment log already present",
                                    reward_item["cycle"], pymnt_addr, reward_item["reward"])
                            else:
                                payments_queue.put(reward_item)
                                logger.info("Reward created for cycle %s address %s amount %f tz",
                                             reward_item["cycle"], pymnt_addr, reward_item["reward"])

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
                nb_blocks_remaining = (current_cycle+1) * BLOCKS_PER_CYCLE - current_level

                logger.debug("Wait until next cycle, for {} blocks".format(nb_blocks_remaining))

                # wait until current cycle ends
                time.sleep(nb_blocks_remaining * BLOCK_TIME_IN_SEC)

        # end of endless loop
        return

    def level_to_cycle(self, level):
        return floor(level / BLOCKS_PER_CYCLE)

    def get_current_cycle(self):
        return self.level_to_cycle(self.get_current_level())

    def get_current_level(self):
        resp = requests.get(HEAD_API_URL)
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /head/ {}'.format(resp.status_code))
        root = resp.json()
        current_level = int(root["level"])

        return current_level

    def get_rewards_for_cycle_map(self, cycle):
        resp = requests.get(REWARDS_SPLIT_API_URL.format(BAKING_ADDRESS, cycle, 0))
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /tasks/ {}'.format(resp.status_code))
        root = resp.json()
        return root


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
                reward_item = payments_queue.get(True)

                pymnt_addr = reward_item["address"]
                pymnt_amnt = reward_item["reward"]
                pymnt_cycle = reward_item["cycle"]

                cmd = COMM_TRANSFER.format(pymnt_amnt, pymnt_addr)

                logger.debug("Reward payment attempt for cycle %s address %s amount %f tz", reward_item["cycle"],reward_item["address"], reward_item["reward"])

                # execute client
                process = subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE)
                process.wait()

                if process.returncode == 0:
                    pymt_log = PAYMNETS_DIR + "/" + str(pymnt_cycle) + "/" + pymnt_addr + '.txt'

                    # check and create required directories
                    if not os.path.exists(os.path.dirname(pymt_log)):
                        os.makedirs(os.path.dirname(pymt_log))

                    # create empty payment log file
                    with open(pymt_log, 'w') as f:
                        f.write('')

                    logger.info("Reward paid for cycle %s address %s amount %f tz", reward_item["cycle"],
                                 reward_item["address"], reward_item["reward"])
                else:
                    logger.warning("Reward NOT paid for cycle %s address %s amount %f tz: Reason client failed!",
                                    reward_item["cycle"], reward_item["address"], reward_item["reward"])
            except Exception as e:
                logger.error("Error at reward payment", e)

        return


if __name__ == '__main__':
    p = ProducerThread(name='producer')
    p.start()

    for i in range(NB_CONSUMERS):
        c = ConsumerThread(name='consumer' + str(i))
        time.sleep(1)
        c.start()
    time.sleep(2)
