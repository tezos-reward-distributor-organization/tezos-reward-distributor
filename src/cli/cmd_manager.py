import subprocess


class CommandManager:
    def __init__(self, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose

    def send_request(self, cmd, verbose_override=None):

        verbose = self.verbose

        if verbose_override is not None:
            verbose = verbose_override

        if verbose:
            print("--> Verbose : Command is |{}|".format(cmd))

        # execute client
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        bytes = []

        for b in process.stdout:
            bytes.append(b)

        # if no response in stdout, read stderr
        if not bytes:
            if verbose:
                print("--- Verbose : Nothing in stdout, reading stderr...")
            for b in process.stderr:
                bytes.append(b)

        process.wait()

        buffer = b''.join(bytes).decode('utf-8')
        buffer = buffer.strip()

        if verbose:
            print("<-- Verbose : Answer is |{}|".format(buffer))

        return buffer
