import requests

from exception.tzstats import TzStatsException
from log_config import main_logger

logger = main_logger

rewards_split_call = '/tables/income?address={}&cycle={}'

PREFIX_API = {'MAINNET': {'API_URL': 'https://api.tzstats.com'},
              'ZERONET': {'API_URL': 'https://api.zeronet.tzstats.com'},
              'BABYLONNET': {'API_URL': 'https://api.babylonnet.tzstats.com'}
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
        root = {"delegate_staking_balance": 0, "delegators_nb": 0, "delegators_balance": [], "blocks_rewards": 0,
                "endorsements_rewards": 0, "fees": 0, "future_blocks_rewards": 0, "future_endorsements_rewards": 0,
                "gain_from_denounciation": 0, "lost_deposit_from_denounciation": 0, "lost_rewards_denounciation": 0,
                "lost_fees_denounciation": 0}

        uri = self.api['API_URL'] + rewards_split_call.format(self.baking_address, cycle)

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)

        if verbose:
            logger.debug("Response from tzstats is {}".format(resp))

        if resp.status_code != 200:
            # This means something went wrong.
            raise TzStatsException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()

        #root["delegate_staking_balance"] = resp[]

        return root
