from subprocess import STDOUT, check_output, TimeoutExpired

TIMEOUT = "SUBPROCESS_TIMEOUT"


class CommandManager:
    def __init__(self, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose

    def send_request(self, cmd, verbose_override=None, timeout=None):

        verbose = self.verbose

        if verbose_override is not None:
            verbose = verbose_override

        if verbose:
            print("--> Verbose : Command is |{}|".format(cmd))

        try:
            output = check_output(cmd, stderr=STDOUT, timeout=timeout)
        except TimeoutExpired as e:
            raise e

        output = output.strip()

        if verbose:
            print("<-- Verbose : Answer is |{}|".format(output))

        return output
