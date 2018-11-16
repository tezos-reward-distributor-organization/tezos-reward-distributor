import random

import requests

from api.block_api import BlockApi

api_mirror = random.randint(2, 5)  # 1 is over used and not reliable

API = {'MAINNET': {'HEAD_API_URL': 'https://api{}.tzscan.io/v2/head'.format(api_mirror)},
       'ALPHANET': {'HEAD_API_URL': 'http://alphanet-api.tzscan.io/v2/head'},
       'ZERONET': {'HEAD_API_URL': 'http://zeronet-api.tzscan.io/v2/head'}
       }


class TzScanBlockApiImpl(BlockApi):

    def __init__(self, nw):
        super(TzScanBlockApiImpl, self).__init__(nw)

        self.api = API[nw['NAME']]
        if self.api is None:
            raise Exception("Unknown network {}".format(nw))

    def get_current_level(self):
        resp = requests.get(self.api['HEAD_API_URL'])
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /head/ {}'.format(resp.status_code))
        root = resp.json()
        current_level = int(root["level"])

        return current_level
