import subprocess
import re


def send_request(cmd):
    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    bytes = []
    for b in process.stdout:
        bytes.append(b)

    process.wait()

    buffer = b''.join(bytes).decode('utf-8')
    print(buffer)

    return buffer


def clear_terminal_chars(content):
    # get rid of special chars, terminal sequences
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    result = ansi_escape.sub('', content)
    return result


def client_list_known_contracts(client_cmd):
    response = send_request(client_cmd + " list known contracts")

    response = clear_terminal_chars(response)

    dict = {}

    for line in response.splitlines():
        if ":" in line and "Warning" not in line[0:10]:
            alias, pkh = line.split(":", maxsplit=1)
            dict[alias.strip()] = pkh.strip()

    print("known contracts: {}".format(dict))

    return dict


def sign(client_cmd, bytes, key_name):
    response = send_request(client_cmd + " sign bytes 0x03{} for {}".format(bytes, key_name))

    response = clear_terminal_chars(response)

    for line in response.splitlines():
        if "Signature" in line:
            return line.strip("Signature:").strip()

    raise Exception("Signature not found in response ''".format(response))
