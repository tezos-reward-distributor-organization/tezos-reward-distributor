import random

import requests
from api.block_api import BlockApi

from log_config import main_logger

logger = main_logger

API = {'MAINNET': {'HEAD_API_URL': 'https://api%MIRROR%.tzscan.io/v2/head'},
       'ALPHANET': {'HEAD_API_URL': 'http://api.alphanet.tzscan.io/v2/head'},
       'ZERONET': {'HEAD_API_URL': 'http://api.zeronet.tzscan.io/v2/head'}
       }


class TzScanBlockApiImpl(BlockApi):

    def __init__(self, nw):
        super(TzScanBlockApiImpl, self).__init__(nw)

        self.api = API[nw['NAME']]
        if self.api is None:
            raise Exception("Unknown network {}".format(nw))

    def get_current_level(self, verbose=False):
        uri = self.api['HEAD_API_URL'].replace("%MIRROR%", str(random.randint(1, 6)))

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri)
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /head/ {}'.format(resp.status_code))
        root = resp.json()

        if verbose:
            logger.debug("Response from tzscan is: {}".format(root))

        current_level = int(root["level"])

        return current_level
