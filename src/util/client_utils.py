import subprocess


def send_request(cmd):
    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    buffer = ''
    for line in process.stdout:
        buffer = buffer + line

    print(buffer)

    process.wait()

    return buffer


def client_list_known_contracts(client_cmd):
    response = send_request(client_cmd + " list known contracts")

    dict = {}

    for line in response.splitlines():
        if ":" in line:
            alias, pkh = line.split(":", maxsplit=1)
            dict[alias] = pkh

    print(dict)

    return dict
