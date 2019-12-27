import requests

from api.block_api import BlockApi
from exception.api_provider import ApiProviderException
from log_config import main_logger

logger = main_logger

PREFIX_API = {'MAINNET': {'HEAD_API_URL': 'https://api.tzstats.com'},
              'ZERONET': {'HEAD_API_URL': 'https://api.zeronet.tzstats.com'},
              'ALPHANET': {'HEAD_API_URL': 'https://api.babylonnet.tzstats.com'}
            }

class TzStatsBlockApiImpl(BlockApi):

    def __init__(self, nw):
        super(TzStatsBlockApiImpl, self).__init__(nw)

        self.head_api = PREFIX_API[nw['NAME']]
        if self.head_api is None:
            raise Exception("Unknown network {}".format(nw))

    def get_current_level(self, verbose=False):
        uri = self.head_api['HEAD_API_URL'] + '/explorer/block/head'

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)
        root = resp.json()

        if verbose:
            logger.debug("Response from tzstats is: {}".format(root))

        current_level = int(root["height"])

        return current_level