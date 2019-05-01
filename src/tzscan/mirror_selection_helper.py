import random

import requests

from log_config import main_logger

nb_delegators_api = {'MAINNET': {'API_URL': 'http://api%MIRROR%.tzscan.io/v3/head'},
                     'ALPHANET': {'API_URL': 'http://api.alphanet.tzscan.io/v3/head'},
                     'ZERONET': {'API_URL': 'http://api.zeronet.tzscan.io/v3/head'}
                     }

logger = main_logger


class TzScanMirrorSelector:
    def __init__(self, nw) -> None:
        super().__init__()
        self.nw_name = nw['NAME']
        self.mirrors = []

    def initialize(self):
        self.validate_mirrors_endless()

    def get_mirror(self):
        mirror_idx = random.randrange(0, len(self.mirrors))

        return self.mirrors[mirror_idx]

    def validate_mirrors(self):
        tmp_mirrors = []
        for mirror in range(7):
            if self.validate_mirror(mirror):
                tmp_mirrors.append(mirror)

        if not tmp_mirrors:
            logger.error("Unable to find a live tzscan mirror. Consider using RPC api.")

        self.mirrors = tmp_mirrors

        logger.info("Available mirrors are: {}".format(self.mirrors))

    def validate_mirrors_endless(self):

        while True:
            self.validate_mirrors()
            if self.mirrors:
                break

    def validate_mirror(self, mirror):
        uri = nb_delegators_api[self.nw_name]['API_URL']
        uri = uri.replace("%MIRROR%", str(mirror))

        resp = requests.get(uri)

        return resp.status_code == 200
