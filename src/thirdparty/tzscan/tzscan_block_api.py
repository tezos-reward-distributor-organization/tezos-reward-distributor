import requests

from api.block_api import BlockApi
from exception.tzscan import TzScanException
from log_config import main_logger
from thirdparty.tzscan.tzscan_utility import rand_mirror

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

    def __init__(self, nw):
        super(TzScanBlockApiImpl, self).__init__(nw)

        self.head_api = HEAD_API[nw['NAME']]
        if self.head_api is None:
            raise Exception("Unknown network {}".format(nw))

        self.revelation_api = REVELATION_API[nw['NAME']]

    def get_current_level(self, verbose=False):
        uri = self.head_api['HEAD_API_URL'].replace("%MIRROR%", str(rand_mirror()))

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri)
        if resp.status_code != 200:
            # This means something went wrong.
            raise TzScanException('GET {} {}'.format(uri, resp.status_code))
        root = resp.json()

        if verbose:
            logger.debug("Response from tzscan is: {}".format(root))

        current_level = int(root["level"])

        return current_level

    def get_revelation(self, pkh, verbose=False):
        uri = self.revelation_api['HEAD_API_URL'].replace("%MIRROR%", str(rand_mirror())).replace("%PKH%", pkh)

        if verbose:
            logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri)
        if resp.status_code != 200:
            # This means something went wrong.
            raise TzScanException('GET {} {}'.format(uri, resp.status_code))
        root = resp.json()

        if verbose:
            logger.debug("Response from tzscan is: {}".format(root))

        return len(root) > 0

def test_get_revelation():
    address_api = TzScanBlockApiImpl({"NAME":"ALPHANET"})
    address_api.get_revelation("tz3WXYtyDUNL91qfiCJtVUX746QpNv5i5ve5")

if __name__ == '__main__':
    test_get_revelation()