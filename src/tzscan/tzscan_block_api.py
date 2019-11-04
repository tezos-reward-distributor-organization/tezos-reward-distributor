import requests

from api.block_api import BlockApi
from exception.tzscan import TzScanException
from log_config import main_logger

logger = main_logger

HEAD_API = {'MAINNET': {'HEAD_API_URL': 'https://api%MIRROR%.tzscan.io/v2/head'},
            'ALPHANET': {'HEAD_API_URL': 'http://api.alphanet.tzscan.io/v2/head'},
            'ZERONET': {'HEAD_API_URL': 'http://api.zeronet.tzscan.io/v2/head'}
            }

REVELATION_API = {'MAINNET': {'HEAD_API_URL': 'https://api%MIRROR%.tzscan.io/v1/operations/%PKH%?type=Reveal'},
                  'ALPHANET': {'HEAD_API_URL': 'https://api.alphanet.tzscan.io/v1/operations/%PKH%?type=Reveal'},
                  'ZERONET': {'HEAD_API_URL': 'https://api.zeronet.tzscan.io/v1/operations/%PKH%?type=Reveal'}
                  }


class TzScanBlockApiImpl(BlockApi):

    def __init__(self, nw, mirror_selector):
        super(TzScanBlockApiImpl, self).__init__(nw)

        self.head_api = HEAD_API[nw['NAME']]
        if self.head_api is None:
            raise Exception("Unknown network {}".format(nw))

        self.revelation_api = REVELATION_API[nw['NAME']]
        self.mirror_selector = mirror_selector

    def get_current_level(self, verbose=False):
        uri = self.head_api['HEAD_API_URL'].replace("%MIRROR%", str(self.mirror_selector.get_mirror()))

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)
        if resp.status_code != 200:
            # This means something went wrong.
            self.mirror_selector.validate_mirrors()
            raise TzScanException('GET {} {}'.format(uri, resp.status_code))
        root = resp.json()

        if verbose:
            logger.debug("Response from tzscan is: {}".format(root))

        current_level = int(root["level"])

        return current_level

    def get_revelation(self, pkh, verbose=False):
        uri = self.revelation_api['HEAD_API_URL'].replace("%MIRROR%", str(self.mirror_selector.get_mirror())).replace("%PKH%", pkh)

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)
        if resp.status_code != 200:
            # This means something went wrong.
            self.mirror_selector.validate_mirrors()
            raise TzScanException('GET {} {}'.format(uri, resp.status_code))
        root = resp.json()

        if verbose:
            logger.debug("Response from tzscan is: {}".format(root))

        return len(root) > 0
