import subprocess
import re

def send_request(cmd):
    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    bytes=[]
    for b in process.stdout:
        bytes.append(b)

    process.wait()

    buffer = b''.join(bytes).decode('utf-8')
    print(buffer)

    return buffer


def client_list_known_contracts(client_cmd):
    response = send_request(client_cmd + " list known contracts")

    # get rid of special chars, terminal sequences
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    response = ansi_escape.sub('', response)


    dict = {}

    for line in response.splitlines():
        if ":" in line and "Warning" not in line[0:10]:
            alias, pkh = line.split(":", maxsplit=1)
            dict[alias] = pkh

    print("known contracts: {}",dict)

    return dict
