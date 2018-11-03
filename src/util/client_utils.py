import subprocess
import re

import os

DOCKER_CLIENT_EXE = "%network%.sh client"
REGULAR_CLIENT_EXE = "tezos-client"


def get_client_path(search_paths, docker=None, network_config=None):
    client_exe = REGULAR_CLIENT_EXE
    if docker:
        client_exe = DOCKER_CLIENT_EXE.replace("%network%", network_config['NAME'].lower())
    for search_path in search_paths:
        expanded_path = os.path.expanduser(search_path)
        client_path = os.path.join(expanded_path, client_exe)
        if os.path.isfile(client_path):
            return client_path

    raise Exception("Client executable not found. Review -E and -D parameters")


def send_request(cmd, verbose=None):
    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    bytes = []
    for b in process.stdout:
        bytes.append(b)

    process.wait()

    buffer = b''.join(bytes).decode('utf-8')

    if verbose:
        print(buffer)

    return buffer


def check_response(response):
    if "Error:" in response or "Unexpected server answer" in response:
        return False
    return True


def clear_terminal_chars(content):
    # get rid of special chars, terminal sequences
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    result = ansi_escape.sub('', content)
    return result


def client_list_known_contracts(client_cmd, verbose=None):
    response = send_request(client_cmd + " list known contracts")

    response = clear_terminal_chars(response)

    dict = {}

    for line in response.splitlines():
        if ":" in line and "Warning" not in line[0:10]:
            alias, pkh = line.split(":", maxsplit=1)
            dict[alias.strip()] = pkh.strip()

    if verbose:
        print("known contracts: {}".format(dict))

    return dict


def sign(client_cmd, bytes, key_name):
    response = send_request(client_cmd + " sign bytes 0x03{} for {}".format(bytes, key_name))

    response = clear_terminal_chars(response)

    for line in response.splitlines():
        if "Signature" in line:
            return line.strip("Signature:").strip()

    raise Exception("Signature not found in response ''".format(response))
