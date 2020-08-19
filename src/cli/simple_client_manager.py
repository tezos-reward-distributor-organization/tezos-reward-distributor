from cli.cmd_manager import CommandManager
from exception.client import ClientException


class SimpleClientManager:
    def __init__(self, client_path, node_addr, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose
        self.client_path = client_path
        self.cmd_manager = CommandManager(verbose)
        self.node_hostname = "127.0.0.1"
        self.node_port = 8732

        # Need to split host:port, default port to 8732 if not specified
        if node_addr is not None:
            parts = node_addr.split(":")
            self.node_hostname = parts[0]
            self.node_port = 8732 if len(parts) == 1 else parts[1]

    def get_node_addr(self) -> str:
        return "{}:{}".format(self.node_hostname, self.node_port)

    def send_request(self, cmd, verbose_override=None, timeout=None):
        # Build command with flags
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
