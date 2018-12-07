import random
from math import ceil

import math
import requests

import NetworkConfiguration
from api.reward_api import RewardApi

from log_config import main_logger

MAX_PER_PAGE = 50

logger = main_logger

nb_delegators_call = 'nb_delegators/{}?cycle={}'
rewards_split_call = 'rewards_split/{}?cycle={}&p={}&number={}'

API = {'MAINNET': {'API_URL': 'http://api%MIRROR%.tzscan.io/v1/'},
       'ALPHANET': {'API_URL': 'http://api.alphanet.tzscan.io/v1/'},
       'ZERONET': {'API_URL': 'http://api.zeronet.tzscan.io/v1/'}
       }


class TzScanRewardApiImpl(RewardApi):

    def __init__(self, nw, baking_address):
        super(TzScanRewardApiImpl, self).__init__()

        self.api = API[nw['NAME']]
        if self.api is None:
            raise Exception("Unknown network {}".format(nw))

        self.baking_address = baking_address

    def get_nb_delegators(self, cycle, verbose=False):
        uri = self.api['API_URL'].replace("%MIRROR%", str(self.rand_mirror())) + nb_delegators_call.format(
            self.baking_address, cycle)

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri)
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET {} {}'.format(uri, resp.status_code))
        root = resp.json()

        if verbose:
            logger.debug("Response from tzscan is {}".format(root))

        return root

    def rand_mirror(self):
        mirror = random.randint(1, 6)

        if mirror == 4:# has problem lately
            mirror = 3

        return mirror

    def get_rewards_for_cycle_map(self, cycle, verbose=False):
        #############
        nb_delegators = self.get_nb_delegators(cycle, verbose)[0]
        nb_delegators_remaining = nb_delegators

        p = 0
        root = {"delegate_staking_balance": 0, "delegators_nb": 0, "delegators_balance": [], "blocks_rewards": 0,
                "endorsements_rewards": 0, "fees": 0, "future_blocks_rewards": 0, "future_endorsements_rewards": 0,
                "gain_from_denounciation": 0, "lost_deposit_from_denounciation": 0, "lost_rewards_denounciation": 0,
                "lost_fees_denounciation": 0}

        while nb_delegators_remaining > 0:
            uri = self.api['API_URL'].replace("%MIRROR%", str(self.rand_mirror())) + rewards_split_call. \
                format(self.baking_address, cycle, p, min(MAX_PER_PAGE, nb_delegators_remaining))

            if verbose:
                logger.debug("Requesting {}".format(uri))

            resp = requests.get(uri)

            if verbose:
                logger.debug("Response from tzscan is {}".format(resp))

            if resp.status_code != 200:
                # This means something went wrong.
                raise Exception('GET {} {}'.format(uri, resp.status_code))

            if p == 0:  # keep first result as basis; append 'delegators_balance' from other responses
                root = resp.json()
            else:  # only take 'delegators_balance' list and append to 'delegators_balance' list in root
                root["delegators_balance"].extend(resp.json()["delegators_balance"])

            nb_delegators_remaining = nb_delegators_remaining - MAX_PER_PAGE
            p = p + 1

        return root


if __name__ == '__main__':
    api = TzScanRewardApiImpl(NetworkConfiguration.network_config_map['ZERONET'],
                              "tz1YZReTLamLhyPLGSALa4TbMhjjgnSi2cqP")
    root = api.get_rewards_for_cycle_map(2539)
    print(root)
