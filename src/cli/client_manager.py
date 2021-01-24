import requests
import json
import os
from datetime import datetime

from Constants import TEZOS_RPC_PORT
from exception.client import ClientException
from log_config import main_logger, verbose_logger

logger = main_logger

COMM_BOOTSTRAP = "{}/monitor/bootstrapped"


class ClientManager:
    def __init__(self, node_endpoint, signer_endpoint) -> None:
        super().__init__()
        self.node_endpoint = node_endpoint
        if self.node_endpoint.find('http') == -1:
            self.node_endpoint = 'http://' + self.node_endpoint
        if len(self.node_endpoint.split(':')) < 3:
            self.node_endpoint += f':{TEZOS_RPC_PORT}'
        self.signer_endpoint = signer_endpoint

    def get_node_url(self) -> str:
        return self.node_endpoint

    def request_url(self,
                    cmd,
                    timeout=None,
                    verbose_override=True):
        if verbose_override:
            verbose_logger.debug("--> Verbose : Command is |{}|".format(cmd))
        url = self.get_node_url() + cmd
        response = requests.get(url, timeout=timeout)
        if not (response.status_code == 200):
            logger.debug("Error, request ->{}<-,".format(url))
            logger.debug("---")
            logger.debug("Error, response ->{}<-".format(response.text))
            return response.status_code, ""
        output = response.json()
        verbose_logger.debug("<-- Verbose : Answer is |{}|".format(output))
        return response.status_code, output

    def request_url_post(self,
                         cmd,
                         json_params,
                         timeout=None,
                         verbose_override=True):
        if verbose_override:
            verbose_logger.debug("--> Verbose : Command is |{}|, Params are |{}|".format(cmd, json_params))
        url = self.get_node_url() + cmd
        headers = {'content-type': "application/json", 'cache-control': "no-cache"}
        response = requests.request("POST", url, data=json_params, headers=headers, timeout=timeout)
        if not (response.status_code == 200):
            logger.debug("Error, request ->{}<-, params ->{}<-,".format(url, json_params))
            logger.debug("---")
            logger.debug("Error, response ->{}<-".format(response.text))
            return response.status_code, ""
        output = response.json()
        verbose_logger.debug("<-- Verbose : Answer is |{}|".format(output))
        return response.status_code, output

    def sign(self, bytes, key_name, timeout=None):
        json_params = json.dumps('03' + bytes)
        signer_url = self.signer_endpoint
        cmd = f'keys/{key_name}'
        url = os.path.join(signer_url, cmd)
        response = requests.request("POST", url, data=json_params, timeout=timeout)
        if not (response.status_code == 200):
            raise ClientException("Error at signing: '{}'".format(response.text))
        else:
            response = response.json()
            return response['signature']

    def check_pkh_known_by_signer(self, key_name, timeout=None):
        signer_url = self.signer_endpoint
        cmd = f'keys/{key_name}'
        url = os.path.join(signer_url, cmd)
        response = requests.get(url, timeout=timeout)
        if not (response.status_code == 200):
            raise ClientException(f"Please import the secret key to the signer before using payment address {key_name} "
                                  f"'{response.text}'")
        else:
            response = response.json()
            if 'public_key' in response:
                return True

    def get_authorized_keys(self, key_name, timeout=None):
        signer_url = self.signer_endpoint
        cmd = 'authorized_keys'
        url = os.path.join(signer_url, cmd)
        response = requests.get(url, timeout=timeout)
        if not (response.status_code == 200):
            raise ClientException(f"Please import the secret key to the signer before using payment address {key_name} "
                                  f"'{response.text}'")
        else:
            response = response.json()
            if 'public_key' in response:
                return True

    def get_bootstrapped(self):
        # /monitor/bootstrapped is a stream of data that only terminates
        # after the node is bootstrapped. Instead, we want to grab the most
        # recent timestamp, present message to user, sleep a bit, then try again.
        count = 0
        boot_resp = {}

        try:
            response = requests.get(COMM_BOOTSTRAP.format(self.get_node_url()), timeout=5, stream=True)
            for line in response.iter_lines(chunk_size=256):
                if line and count < 5:
                    boot_resp = json.loads(line)
                    logger.debug("Bootstrap Monitor: {}".format(boot_resp))
                    count += 1
                else:
                    response.close()
                    break

            boot_time = datetime.strptime(boot_resp["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
            logger.debug("RPC node bootstrap time is '{}'".format(boot_time))

            return boot_time

        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            logger.debug("RPC node bootstrap timeout. Will try again.")

        # Return unix epoch if cannot determine
        return datetime.min
