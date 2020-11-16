import os
import re
from log_config import main_logger

DOCKER_CLIENT_EXE = "%network%.sh"
DOCKER_CLIENT_EXE_SUFFIX = " client"
REGULAR_CLIENT_EXE = "tezos-client"

logger = main_logger


def get_client_path(search_paths, docker=None, network_name=None):
    client_exe = REGULAR_CLIENT_EXE
    if docker:
        client_exe = DOCKER_CLIENT_EXE.replace("%network%", network_name.lower())
    for search_path in search_paths:
        expanded_path = os.path.expanduser(search_path)
        client_path = os.path.join(expanded_path, client_exe)
        if os.path.isfile(client_path):
            return client_path + DOCKER_CLIENT_EXE_SUFFIX if docker else client_path

        logger.debug("Not found {}".format(client_path))

    raise Exception("Client executable not found. Review --executable_dirs, --docker and --network parameters")


def check_response(response):
    if "Error:" in response or "error" in response or "invalid" in response or "Unexpected server answer" in response:
        return False
    return True


def get_operation_hash(client_response):
    for line in client_response.splitlines():
        if line.startswith("Operation hash"):
            # example hash line
            # Operation hash: oo8HjBGmZ4Pm7VUGbRPVV1i3k6CsuSsRtL1gPnwruXAj1Wd7fWW
            # split using ':' and take second part then get rid of leading, trailing spaces
            return line.split(":")[1].strip()
    return "not-found"


def clear_terminal_chars(content):
    # get rid of special chars, terminal sequences
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    result = ansi_escape.sub('', content)
    return result


def not_indicator_line(line):
    return "Warning" not in line[0:15] and "Disclaimer" not in line[0:15]
