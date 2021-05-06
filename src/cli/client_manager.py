import requests
import json
import os
from datetime import datetime
from http import HTTPStatus

from Constants import TEZOS_RPC_PORT
from exception.client import ClientException
from log_config import main_logger, verbose_logger

logger = main_logger

COMM_BOOTSTRAP = "{}/monitor/bootstrapped"
MAX_NB_TRIES = 3

class ClientManager:
    def __init__(self, node_endpoint, signer_endpoint) -> None:
        super().__init__()
        self.node_endpoint = node_endpoint
        if self.node_endpoint.find('http') == -1:
            if self.node_endpoint.find('443') == -1:
                self.node_endpoint = 'http://' + self.node_endpoint
            else:
                self.node_endpoint = 'https://' + self.node_endpoint
                logger.info("Node endpoint URL points to an SSL endpoint. Using HTTPS protocol prefix.")
        if len(self.node_endpoint.split(':')) < 3:
            self.node_endpoint += f':{TEZOS_RPC_PORT}'
        self.signer_endpoint = signer_endpoint

    def get_node_url(self) -> str:
        return self.node_endpoint

    def request_url(self,
                    cmd,
                    timeout=None):

        verbose_logger.debug("--> Verbose : Command is |{}|".format(cmd))

        url = self.get_node_url() + cmd
        response = self._do_request(method="GET",
                                    url=url,
                                    timeout=timeout)
        if response is None:
            return -1, "TimeOut"

        if response.status_code != HTTPStatus.OK:
            return response.status_code, "Code" + str(response.status_code)

        output = response.json()
        verbose_logger.debug("<-- Verbose : Answer is |{}|".format(output))
        return response.status_code, output

    def request_url_post(self,
                         cmd,
                         json_params,
                         timeout=None):

        verbose_logger.debug("--> Verbose : Command is |{}|, Params are |{}|".format(cmd, json_params))

        url = self.get_node_url() + cmd
        headers = {'content-type': "application/json", 'cache-control': "no-cache"}
        try:
            response = self._do_request(method="POST",
                                        url=url,
                                        json_params=json_params,
                                        headers=headers,
                                        timeout=timeout)
        except Exception:
            return -1, "TimeOut"

        if response.status_code != HTTPStatus.OK:
            return response.status_code, "Code" + str(response.status_code)

        output = response.json()
        verbose_logger.debug("<-- Verbose : Answer is |{}|".format(output))
        return response.status_code, output

    def sign(self, bytes, key_name, timeout=None):
        json_params = json.dumps('03' + bytes)
        signer_url = self.signer_endpoint
        cmd = f'keys/{key_name}'
        url = os.path.join(signer_url, cmd)
        headers = {'content-type': "application/json"}
        response = self._do_request(method="POST",
                                    url=url,
                                    json_params=json_params,
                                    headers=headers,
                                    timeout=timeout)

        if response is None:
            raise ClientException("Unknown Error at signing. Please consult the verbose logs!")
        if response.status_code != HTTPStatus.OK:
            raise ClientException("Error at signing. Make sure tezos-signer is up and running 'tezos-signer launch http signer': '{}'".format(response.text))
        else:
            response = response.json()
            return response['signature']

    def check_pkh_known_by_signer(self, key_name, timeout=None):

        signer_url = self.signer_endpoint
        cmd = f'keys/{key_name}'
        url = os.path.join(signer_url, cmd)

        signer_exception = f'Error querying the signer at url {signer_url}. \n' \
                           f'Please make sure you have started the signer using "./tezos-signer launch http signer", \n' \
                           f'imported the secret key of the payout address {key_name}, \n' \
                           f'and specified the URL of signer using the flag -E http://<signer_addr>:<port> (default http://127.0.0.1:6732)'

        try:
            response = self._do_request(method="GET",
                                        url=url,
                                        timeout=timeout)
        except Exception as e:
            raise ClientException(f'Exception: {e}\n{signer_exception}')
        if response.status_code != HTTPStatus.OK:
            raise ClientException(f'{response.text}\n{signer_exception}')
        else:
            response = response.json()
            if 'public_key' not in response:
                raise ClientException(f'The secret key of the payout address {key_name} was not imported to the signer!\n'
                                      f'{signer_exception}')

    def get_authorized_keys(self, timeout=None):

        signer_url = self.signer_endpoint
        cmd = 'authorized_keys'
        url = os.path.join(signer_url, cmd)

        signer_exception = f'Error querying the signer at url {signer_url}. \n' \
                           f'Please make sure to start the signer using "./tezos-signer launch http signer", \n' \
                           f'import the secret key of the payout address \n' \
                           f'and specify the url using the flag -E http://<signer_addr>:<port> (default http://127.0.0.1:6732)'

        try:
            response = self._do_request(method="GET",
                                        url=url,
                                        timeout=timeout)
        except Exception as e:
            raise ClientException(f'Exception: {e}\n{signer_exception}')
        if response.status_code != HTTPStatus.OK:
            raise ClientException(f'{response.text}\n{signer_exception}')
        else:
            response = response.json()
            return response

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

    def _do_request(self,
                    method,
                    url,
                    json_params=None,
                    headers=None,
                    timeout=None):

        try_i = 0
        response = None
        while response is None and try_i < MAX_NB_TRIES:
            try:
                try_i += 1
                response = requests.request(method=method,
                                            url=url,
                                            data=json_params,
                                            headers=headers,
                                            timeout=timeout)
            except Exception as e:
                logger.error(f"Error, request ->{url}<-, params ->{json_params}<-,\n---\n"
                             f"Error, exception ->{e}<-")
                # If all MAX_NB_TRIES tries were not successful
                if try_i == MAX_NB_TRIES - 1:
                    raise Exception(e)
        if response is None:
            return
        # If request returns failed code
        if response.status_code != HTTPStatus.OK:
            logger.error(f"Error, request ->{method} {url}<-, params ->{json_params}<-,\n---\n"
                         f"Error, response ->{response.text}<-")
        return response
