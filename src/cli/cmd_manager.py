import os
from subprocess import STDOUT, check_output, TimeoutExpired, CalledProcessError
from log_config import main_logger
from util.client_utils import clear_terminal_chars

TIMEOUT = "SUBPROCESS_TIMEOUT"
logger = main_logger


class CommandManager:
    def __init__(self, verbose=None) -> None:
        super().__init__()
        self.verbose = verbose

    def exec(self, cmd, verbose_override=None, timeout=None):
        return self.execute(cmd, verbose_override, timeout)[1]

    def execute(self, cmd, verbose_override=None, timeout=None):

        verbose = self.verbose

        if verbose_override is not None:
            verbose = verbose_override

        if verbose:
            logger.debug("--> Verbose : Command is |{}|".format(cmd))

        try:
            os.environ["TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER"] = "Y"
            output = check_output(cmd, shell=True, stderr=STDOUT, timeout=timeout, encoding='utf8')
        except TimeoutExpired as e:
            logger.info("Command timed out")
            raise e
        except CalledProcessError as e:
            logger.info("Command failed, error is |{}|".format(e.output))
            return False, e.output

        # output = output.decode('utf-8')
        output = clear_terminal_chars(output)
        output = output.strip()

        if verbose:
            logger.debug("<-- Verbose : Answer is |{}|".format(output))

        return True, output
