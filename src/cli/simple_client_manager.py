from cli.cmd_manager import CommandManager
from exception.client import ClientException


class SimpleClientManager:
    def __init__(self, client_path, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose
        self.client_path = client_path
        self.cmd_manager = CommandManager(verbose)

    def send_request(self, cmd, verbose_override=None, timeout=None):
        whole_cmd = self.client_path + cmd

        return self.cmd_manager.execute(whole_cmd, verbose_override, timeout=timeout)

    def sign(self, bytes, key_name, verbose_override=None):
        result, response = self.send_request(" sign bytes 0x03{} for {}".format(bytes, key_name), verbose_override=verbose_override)

        if not result:
            raise ClientException("Error at signing: '{}'".format(response))

        for line in response.splitlines():
            if "Signature" in line:
                return line.strip("Signature:").strip()

        raise ClientException("Signature not found in response '{}'. Signed with key '{}'".format(response, key_name))

if __name__ == '__main__':
    response = """Warning:
  
                 This is NOT the Tezos Mainnet.
  
      The node you are connecting to claims to be running on the
                 Tezos Zeronet DEVELOPMENT NETWORK.
           Do NOT use your fundraiser keys on this network.
  Zeronet is a testing network, with free tokens and frequent resets.

Signature: edsigtooXY4QHwhycxkhkfVUqusWYqHemb51kaEh7ATtiigxjrLaVcPMttKBMLFzNtb7SmEc7Vn53PbXWSPnGHmHavTfhNYwiut"""

    print(response)
    for line in response.splitlines():
        print (line)
    for line in response.splitlines():
        #if "Signature" in line:
        print (line.strip("Signature"))