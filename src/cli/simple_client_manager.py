import requests
import json
from datetime import datetime
from Constants import TEZOS_RPC_PORT
from cli.cmd_manager import CommandManager
from exception.client import ClientException
from log_config import main_logger

logger = main_logger

COMM_BOOTSTRAP = "{}/monitor/bootstrapped"


class SimpleClientManager:
    def __init__(self, client_path, node_addr, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose
        self.client_path = client_path
        self.cmd_manager = CommandManager(verbose)
        self.node_hostname = "127.0.0.1"
        self.node_port = TEZOS_RPC_PORT
        self.tls_on = False

        # Need to split host:port, default port to 8732 if not specified
        if node_addr is not None:
            # set tls to true if node address contains https
            self.tls_on = (node_addr.find('https://') != -1)
            # Remove potential protocol prefixes
            node_addr = node_addr.replace('https://', '')
            node_addr = node_addr.replace('http://', '')
            parts = node_addr.split(":")
            self.node_hostname = parts[0]
            self.node_port = TEZOS_RPC_PORT if len(parts) == 1 else parts[1]

    def get_node_addr(self) -> str:
        return "{}:{}".format(self.node_hostname, self.node_port)

    def get_node_url(self) -> str:
        return "{}://{}:{}".format(
               "https" if self.tls_on else "http", self.node_hostname, self.node_port)

    def send_request(self, cmd, verbose_override=None, timeout=None):
        # Build command with flags
        if self.tls_on:
            whole_cmd = "{} -S -A {} -P {} {}".format(self.client_path, self.node_hostname, self.node_port, cmd)
        else:
            whole_cmd = "{} -A {} -P {} {}".format(self.client_path, self.node_hostname, self.node_port, cmd)
        return self.cmd_manager.execute(whole_cmd, verbose_override, timeout=timeout)

    def sign(self, bytes, key_name, verbose_override=None):
        result, response = self.send_request(" sign bytes 0x03{} for {}".format(bytes, key_name), verbose_override=verbose_override)

        if not result:
            raise ClientException("Error at signing: '{}'".format(response))

        for line in response.splitlines():
            if "Signature" in line:
                return line.replace("Signature:", "").strip()

        raise ClientException("Signature not found in response '{}'. Signed with key '{}'".format(response, key_name))

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
