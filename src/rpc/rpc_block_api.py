import requests
from api.block_api import BlockApi
from exception.api_provider import ApiProviderException
from log_config import main_logger

logger = main_logger.getChild("rpc_block_api")

COMM_HEAD = "{}/chains/main/blocks/head"
COMM_DELEGATES = "{}/chains/main/blocks/head/context/delegates/{}"
COMM_REVELATION = "{}/chains/main/blocks/head/context/contracts/{}/manager_key"


class RpcBlockApiImpl(BlockApi):
    def __init__(self, nw, node_url):
        super(RpcBlockApiImpl, self).__init__(nw)
        self.node_url = node_url
        logger.debug("RpcBlockApiImpl - node_url {}".format(self.node_url))

    def get_current_level(self, verbose=False):
        try:
            response = requests.get(COMM_HEAD.format(self.node_url), timeout=5)
            head = response.json()
            current_level = int(head["metadata"]["level_info"]["level"])
            return current_level
        except requests.exceptions.RequestException as e:
            message = "[RpcBlockApiImpl] - Unable to fetch /head: {:s}".format(str(e))
            logger.error(message)
            raise ApiProviderException(message)

    def get_current_cycle(self, verbose=False):
        try:
            response = requests.get(COMM_HEAD.format(self.node_url), timeout=5)
            head = response.json()
            current_cycle = int(head["metadata"]["level_info"]["cycle"])
            return current_cycle
        except requests.exceptions.RequestException as e:
            message = "[RpcBlockApiImpl] - Unable to fetch /head: {:s}".format(str(e))
            logger.error(message)
            raise ApiProviderException(message)

    def get_revelation(self, pkh, verbose=False):
        try:
            response = requests.get(COMM_REVELATION.format(self.node_url, pkh))
            manager_key = response.json()
            logger.debug("Manager key is '{}'".format(manager_key))
            return manager_key and \
              manager_key != "null" and ( \
              (manager_key.startswith("edpk") and len(manager_key) == 54) or \
              (manager_key.startswith(("p2pk", "sppk")) and len(manager_key) == 55))

        except requests.exceptions.RequestException as e:
            message = "[{}] - Unable to fetch revelation: {:s}".format(__class__.__name__, str(e))
            logger.error(message)
            raise ApiProviderException(message)

    def get_delegatable(self, pkh):
        try:
            response = requests.get(COMM_DELEGATES.format(self.node_url, pkh))
            delegates = response.json()
            return "delegated_contracts" in delegates and not bool(delegates["deactivated"])
        except requests.exceptions.RequestException as e:
            message = "[{}] - Unable to fetch delegate: {:s}".format(__class__.__name__, str(e))
            logger.error(message)
            raise ApiProviderException(message)


def test_get_revelation():

    address_api = RpcBlockApiImpl({"NAME": "ALPHANET"}, "127.0.0.1:8732")
    print(address_api.get_revelation("tz1N5cvoGZFNYWBp2NbCWhaRXuLQf6e1gZrv"))
    print(address_api.get_revelation("KT1FXQjnbdqDdKNpjeM6o8PF1w8Rn2j8BmmG"))
    print(address_api.get_revelation("tz1YVxe7FFisREKXWNxdrrwqvw3o2jeXzaNb"))
