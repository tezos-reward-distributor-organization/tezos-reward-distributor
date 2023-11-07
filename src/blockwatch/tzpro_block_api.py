import requests
from api.block_api import BlockApi
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger
from Constants import TZPRO_API_URL

logger = main_logger


class TzProBlockApiImpl(BlockApi):
    def __init__(self, nw, tzpro_api_key):
        super(TzProBlockApiImpl, self).__init__(nw)

        self.head_api = TZPRO_API_URL[nw["NAME"]]
        if self.head_api is None:
            raise Exception("Unknown network {}".format(nw))

        if tzpro_api_key == "":
            raise Exception(
                "Please set a tzpro api key in the config to use this block api!"
            )
        self.key = tzpro_api_key

    def get_current_cycle_and_level(self):
        uri = self.head_api + "/explorer/tip"

        verbose_logger.debug("Requesting {}".format(uri))

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})
        root = resp.json()

        verbose_logger.debug("Response from tzpro is: {}".format(root))

        current_cycle = int(root["cycle"])
        current_level = (
            int(root["height"]) + 1
        )  # Adding one to be in synch with the tzkt API

        return (current_cycle, current_level)

    def get_revelation(self, pkh, verbose=False):
        try:
            uri = self.head_api + "/explorer/account/{}".format(pkh)
            verbose_logger.debug("Requesting {}".format(uri))
            response = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})
            account = response.json()
            return bool(account["is_revealed"])
        except requests.exceptions.RequestException as e:
            message = "[{}] - Unable to fetch revelation: {:s}".format(
                __class__.__name__, str(e)
            )
            logger.error(message)
            raise ApiProviderException(message)

    def get_delegatable(self, pkh):
        try:
            uri = self.head_api + "/explorer/account/{}".format(pkh)
            verbose_logger.debug("Requesting {}".format(uri))
            response = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})
            account = response.json()
            return bool(account.get("is_baker", False))
        except requests.exceptions.RequestException as e:
            message = "[{}] - Unable to fetch delegate: {:s}".format(
                __class__.__name__, str(e)
            )
            logger.error(message)
            raise ApiProviderException(message)
