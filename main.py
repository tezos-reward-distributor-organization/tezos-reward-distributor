import threading
import queue
import time
from math import floor
import logging

import requests

BUF_SIZE = 50
ONE_MILLION = 1000000
NB_FREEZE_CYCLE = 5
BAKING_ADDRESS = "tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj"
BLOCKS_PER_CYCLE = 4096
NB_CONSUMERS = 4
payments_queue = queue.Queue(BUF_SIZE)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(threadName)-9s %(message)s', )


class ProducerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(ProducerThread, self).__init__()
        self.target = target
        self.name = name

        logging.debug('Producer started')

    def run(self):
        while True:
            if not payments_queue.full():
                try:
                    current_cycle = self.get_current_cycle()
                    payment_cycle = current_cycle - NB_FREEZE_CYCLE + 1

                    logging.info("Payment cycle is " + str(payment_cycle))
                    root = self.get_rewards_for_cycle_map(payment_cycle)

                    delegate_staking_balance = int(root["delegate_staking_balance"])
                    blocks_rewards = int(root["blocks_rewards"])
                    endorsements_rewards = int(root["endorsements_rewards"])
                    fees = int(root["fees"])
                    total_rewards = blocks_rewards + endorsements_rewards + fees

                    logging.info("Total rewards=" + str(total_rewards))

                    delegators_balance = root["delegators_balance"]
                    for dbalance in delegators_balance:
                        address = dbalance[0]["tz"]
                        balance = int(dbalance[1])
                        share_rate = balance / delegate_staking_balance
                        reward_share = round(total_rewards * share_rate / ONE_MILLION, 3)
                        reward_item = {"cycle":payment_cycle,"address": address, "reward": reward_share}
                        payments_queue.put(reward_item)

                        logging.info(
                            "Reward created for cycle %s address %s amount %f tz",reward_item["cycle"],reward_item["address"] , reward_item["reward"])

                    time.sleep(60)
                except Exception as e:
                    logging.error("Error at reward calculation",e)
                    time.sleep(10)
        return

    def get_current_cycle(self):
        resp = requests.get('http://api1.tzscan.io/v2/head')
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /head/ {}'.format(resp.status_code))
        root = resp.json()
        current_level = int(root["level"])
        current_cycle = floor(current_level / BLOCKS_PER_CYCLE)

        return current_cycle

    def get_rewards_for_cycle_map(self, cycle):
        resp = requests.get(
            'http://api4.tzscan.io/v1/rewards_split/' + BAKING_ADDRESS + '?cycle=' + str(cycle) + '&p=0')
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /tasks/ {}'.format(resp.status_code))
        root = resp.json()
        return root


class ConsumerThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, verbose=None):
        super(ConsumerThread, self).__init__()
        self.target = target
        self.name = name
        logging.debug('Consumer "%s" created',self.name)
        return

    def run(self):
        while True:
            # wait until a reward is present
            reward_item = payments_queue.get(True)
            time.sleep(60)
            logging.info(
                "Reward paid for cycle %s address %s amount %f tz",reward_item["cycle"], reward_item["address"], reward_item["reward"])

        return


if __name__ == '__main__':
    p = ProducerThread(name='producer')
    p.start()

    for i in range(NB_CONSUMERS):
        c = ConsumerThread(name='consumer' + str(i))
        time.sleep(1)
        c.start()

    time.sleep(2)
