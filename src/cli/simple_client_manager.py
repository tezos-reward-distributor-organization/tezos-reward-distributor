from cli.cmd_manager import CommandManager
from exception.client import ClientException
from util.client_utils import clear_terminal_chars


class SimpleClientManager:
    def __init__(self, client_path, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose
        self.client_path = client_path
        self.cmd_manager = CommandManager(verbose)

    def send_request(self, cmd, verbose_override=None):
        whole_cmd = self.client_path + cmd

        return self.cmd_manager.send_request(whole_cmd, verbose_override)

    def sign(self, bytes, key_name):
        response = self.send_request(" sign bytes 0x03{} for {}".format(bytes, key_name))

        response = clear_terminal_chars(response)

        for line in response.splitlines():
            if "Signature" in line:
                return line.strip("Signature:").strip()

        raise ClientException(
            "Signature not found in response '{}'. Signed with {}".format(response.replace('\n'), 'key_name'))
