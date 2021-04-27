import requests
from api.block_api import BlockApi
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger
from Constants import TZSTATS_PREFIX_API

logger = main_logger


class TzStatsBlockApiImpl(BlockApi):

    def __init__(self, nw):
        super(TzStatsBlockApiImpl, self).__init__(nw)

        self.head_api = TZSTATS_PREFIX_API[nw['NAME']]
        if self.head_api is None:
            raise Exception("Unknown network {}".format(nw))

    def get_current_level(self):
        uri = self.head_api + '/explorer/tip'

        verbose_logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5)
        root = resp.json()

        verbose_logger.debug("Response from tzstats is: {}".format(root))

        current_level = int(root["status"]["blocks"])

        return current_level

    def get_revelation(self, pkh, verbose=False):
        try:
            uri = self.head_api + '/explorer/account/{}'.format(pkh)
            verbose_logger.debug("Requesting {}".format(uri))
            response = requests.get(uri)
            account = response.json()
            return bool(account["is_revealed"])
        except requests.exceptions.RequestException as e:
            message = "[{}] - Unable to fetch revelation: {:s}".format(__class__.__name__, str(e))
            logger.error(message)
            raise ApiProviderException(message)

    def get_delegatable(self, pkh):
        try:
            uri = self.head_api + '/explorer/account/{}'.format(pkh)
            verbose_logger.debug("Requesting {}".format(uri))
            response = requests.get(uri)
            account = response.json()
            return bool(account["is_delegate"]) and bool(account["is_active_delegate"])
        except requests.exceptions.RequestException as e:
            message = "[{}] - Unable to fetch delegate: {:s}".format(__class__.__name__, str(e))
            logger.error(message)
            raise ApiProviderException(message)
