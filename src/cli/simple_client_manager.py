import subprocess

from util.client_utils import clear_terminal_chars


class SimpleClientManager:
    def __init__(self, client_path, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose
        self.client_path = client_path

    def send_request(self, cmd):
        whole_cmd = self.client_path + cmd
        if self.verbose:
            print("Command is |{}|".format(whole_cmd))

        # execute client
        process = subprocess.Popen(whole_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        bytes = []
        for b in process.stdout:
            bytes.append(b)

        process.wait()

        buffer = b''.join(bytes).decode('utf-8')

        if self.verbose:
            print("Answer is |{}|".format(buffer))

        return buffer

    def sign(self, bytes, key_name):
        response = self.send_request(" sign bytes 0x03{} for {}".format(bytes, key_name))

        response = clear_terminal_chars(response)

        for line in response.splitlines():
            if "Signature" in line:
                return line.strip("Signature:").strip()

        raise Exception("Signature not found in response '{}'".format(response.replace('\n', '')))
