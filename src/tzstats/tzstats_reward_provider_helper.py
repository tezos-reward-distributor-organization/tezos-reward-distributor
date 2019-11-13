import requests

from exception.tzstats import TzStatsException
from log_config import main_logger
from tzstats.tzstats_api_constants import *

logger = main_logger

rewards_split_call = '/tables/income?address={}&cycle={}'
delegators_call = '/tables/snapshot?cycle={}&is_selected=1&delegate={}&limit=50000'

PREFIX_API = {'MAINNET': {'API_URL': 'http://api.tzstats.com'},
              'ZERONET': {'API_URL': 'http://api.zeronet.tzstats.com'},
              'BABYLONNET': {'API_URL': 'http://api.babylonnet.tzstats.com'}
            }


class TzStatsRewardProviderHelper:

    def __init__(self, nw, baking_address):
        super(TzStatsRewardProviderHelper, self).__init__()

        self.preserved_cycles = nw['NB_FREEZE_CYCLE']

        self.api = PREFIX_API[nw['NAME']]
        if self.api is None:
            raise TzStatsException("Unknown network {}".format(nw))

        self.baking_address = baking_address

    def get_rewards_for_cycle(self, cycle, expected_reward = False, verbose=False):
        #############
        root = {"delegate_staking_balance": 0, "total_reward_amount": 0, "delegators_balance": {}}

        uri = self.api['API_URL'] + rewards_split_call.format(self.baking_address, cycle)

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)

        if verbose:
            logger.debug("Response from tzstats is {}".format(resp))

        if resp.status_code != 200:
            # This means something went wrong.
            raise TzStatsException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()[0]
        if expected_reward:
            root["total_reward_amount"] = int(1e6 * float(resp[idx_income_expected_income]))
        else:
            root["total_reward_amount"] = int(1e6 * (float(resp[idx_income_baking_income]) + float(resp[idx_income_endorsing_income]) + float(resp[idx_income_seed_income]) +  float(resp[idx_income_fees_income])  -  float(resp[idx_income_lost_accusation_fees]) -  float(resp[idx_income_lost_accusation_rewards]) -  float(resp[idx_income_lost_revelation_fees]) -  float(resp[idx_income_lost_revelation_rewards])))


        uri = self.api['API_URL'] + delegators_call.format(cycle - self.preserved_cycles - 2, self.baking_address)

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)

        if verbose:
            logger.debug("Response from tzstats is {}".format(resp))

        if resp.status_code != 200:
            # This means something went wrong.
            raise TzStatsException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()

        for delegator in resp:
            if delegator[idx_delegator_address] == self.baking_address:
                root["delegate_staking_balance"] = int(1e6 * (float(delegator[idx_baker_balance]) + float(delegator[idx_baker_delegated])))
            else:
                root["delegators_balance"][delegator[idx_delegator_address]] = int(1e6 * float(delegator[idx_delegator_balance]))

        return root
