import requests

from exception.tzstats import TzStatsException
from log_config import main_logger
from tzstats.tzstats_api_constants import *

logger = main_logger

rewards_split_call = '/tables/income?address={}&cycle={}'

PREFIX_API = {'MAINNET': {'API_URL': 'http://api.tzstats.com'},
              'ZERONET': {'API_URL': 'http://api.zeronet.tzstats.com'},
              'BABYLONNET': {'API_URL': 'http://api.babylonnet.tzstats.com'}
            }


class TzStatsRewardProviderHelper:

    def __init__(self, nw, baking_address):
        super(TzStatsRewardProviderHelper, self).__init__()

        self.api = PREFIX_API[nw['NAME']]
        if self.api is None:
            raise TzStatsException("Unknown network {}".format(nw))

        self.baking_address = baking_address

    def get_rewards_for_cycle(self, cycle, verbose=False):
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

        root["total_reward_amount"] = resp[idx_income_total_income] * 1e6 # needs to be more precise -> feature request
        root["delegate_staking_balance"] = resp[idx_income_balance] + resp[idx_income_delegated]
        # root["delegators_balance"] -> feature request

        return root
