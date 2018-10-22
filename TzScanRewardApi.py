import requests

from RewardApi import RewardApi

API = {'MAIN': {'REWARDS_SPLIT_API_URL': 'http://api4.tzscan.io/v1/rewards_split/{}?cycle={}&p={}'},
       'ALPHA': {'REWARDS_SPLIT_API_URL': 'http://alphanet-api.tzscan.io/v1/rewards_split/{}?cycle={}&p={}'},
       'ZERO': {'REWARDS_SPLIT_API_URL': 'http://zeronet-api.tzscan.io/v1/rewards_split/{}?cycle={}&p={}'}
       }


class TzScanRewardApi(RewardApi):

    def __init__(self, nw, baking_address):
        super().__init__()

        self.api = API[nw['NAME']]
        if self.api is None:
            raise Exception("Unknown network {}".format(nw))

        self.baking_address = baking_address

    def get_rewards_for_cycle_map(self, cycle):
        resp = requests.get(self.api['REWARDS_SPLIT_API_URL'].format(self.baking_address, cycle, 0))
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /tasks/ {}'.format(resp.status_code))
        root = resp.json()
        return root
