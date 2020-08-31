import requests
import json

from datetime import datetime
from api.block_api import BlockApi
from log_config import main_logger

logger = main_logger

COMM_BOOTSTRAP = "{}/monitor/bootstrapped"
COMM_HEAD = "{}/chains/main/blocks/head"
COMM_REVELATION = "{}/chains/main/blocks/head/context/contracts/{}/manager_key"

class RpcBlockApiImpl(BlockApi):

    def __init__(self, nw, node_url):
        super(RpcBlockApiImpl, self).__init__(nw)

        self.node_url = node_url

    def get_current_level(self, verbose=False):
        response = requests.get(COMM_HEAD.format(self.node_url), timeout=5)
        head = response.json()
        current_level = int(head["metadata"]["level"]["level"])
        return current_level

    def get_revelation(self, pkh, verbose=False):
        response = requests.get(COMM_REVELATION.format(self.node_url, pkh), timeout=5)
        manager_key = response.json()
        logger.debug("Manager key is '{}'".format(manager_key))
        bool_revelation = manager_key and manager_key!='null'
        return bool_revelation

    def get_bootstrapped(self):
        # /monitor/bootstrapped is a stream of data that only terminates
        # after the node is bootstrapped. Instead, we want to grab the most
        # recent timestamp, present message to user, sleep a bit, then try again.
        count = 0
        boot_resp = {}
        response = requests.get(COMM_BOOTSTRAP.format(self.node_url), timeout=5, stream=True)
        for line in response.iter_lines(chunk_size=256):
            if line and count < 5:
                boot_resp = json.loads(line)
                logger.debug("Bootstrap Monitor: {}".format(boot_resp))
                count += 1
            else:
                response.close()
                break

        boot_time = datetime.strptime(boot_resp["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        logger.debug("Local node bootstrap time is '{}'".format(boot_time))

        return boot_time


def test_get_revelation():

    address_api = RpcBlockApiImpl({"NAME":"ALPHANET"}, "127.0.0.1:8732")
    print(address_api.get_revelation("tz1N5cvoGZFNYWBp2NbCWhaRXuLQf6e1gZrv"))
    print(address_api.get_revelation("KT1FXQjnbdqDdKNpjeM6o8PF1w8Rn2j8BmmG"))
    print(address_api.get_revelation("tz1YVxe7FFisREKXWNxdrrwqvw3o2jeXzaNb"))
