import subprocess
import re

import os

DOCKER_CLIENT_EXE = "%network%.sh"
DOCKER_CLIENT_EXE_SUFFIX=" client"
REGULAR_CLIENT_EXE = "tezos-client"

test_str="""
Warning:
  
                           This is NOT the Tezos Mainnet.
                        The Tezos Mainnet is not yet released.
  
              The node you are connecting to claims to be running on the
                        Tezos Betanet EXPERIMENTAL NETWORK.
      Betanet is a pre-release experimental network and comes with no warranty.
              Use your fundraiser keys on this network AT YOUR OWN RISK.
    All transactions happening on the Betanet are expected to be valid in the Mainnet.
            If in doubt, we recommend that you wait for the Mainnet lunch.

Error:
  Rpc request failed:
     - meth: POST
     - uri: http://localhost:8732/chains/main/blocks/head/helpers/preapply/operations
     - error: Oups! It looks like we forged an invalid HTTP request.
                [ { "protocol": "PsYLVpVvgbLhAhoqAkMFUo6gudkJ9weNXhUYCiLDzcUpFpkk8Wt",
    "branch": "BLh62ZiNsBiLnQZiuUsQzTdXkjWgeLAMryYJywV9z4wCZsjTL8h",
    "contents":
      [ { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1PEZ91VnphKodWSfuvCcjXrA29zfHsgUxt", "fee": "0",
          "counter": "316261", "gas_limit": "200", "storage_limit": "0",
          "amount": "31431000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1Ao8UXNJ9Dz71Wx3m8yzYNdnNQp2peqtMc", "fee": "0",
          "counter": "316262", "gas_limit": "200", "storage_limit": "0",
          "amount": "3117000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT18bVwvyLBR1GAM1rBoiHzEXVNtXb5C3vEU", "fee": "0",
          "counter": "316263", "gas_limit": "200", "storage_limit": "0",
          "amount": "2830000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1HuhLZ3Rg45bRnSVssA6KEVXqbKbjzsmPH", "fee": "0",
          "counter": "316264", "gas_limit": "200", "storage_limit": "0",
          "amount": "1000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT18bVwvyLBR1GAM1rBoiHzEXVNtXb5C3vEU", "fee": "0",
          "counter": "316265", "gas_limit": "200", "storage_limit": "0",
          "amount": "40000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1PEZ91VnphKodWSfuvCcjXrA29zfHsgUxt", "fee": "0",
          "counter": "316266", "gas_limit": "200", "storage_limit": "0",
          "amount": "431000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT18bVwvyLBR1GAM1rBoiHzEXVNtXb5C3vEU", "fee": "0",
          "counter": "316267", "gas_limit": "200", "storage_limit": "0",
          "amount": "75000" },
        { "kind": "transaction",
          "source": "tz1aZoYGSEoGpzWmitPaCJw6HQCkz5YSi1ow",
          "destination": "KT1PEZ91VnphKodWSfuvCcjXrA29zfHsgUxt", "fee": "0",
          "counter": "316268", "gas_limit": "200", "storage_limit": "0",
          "amount": "75000" } ],
    "signature":
      "edsigtiGP1KZTXrjwbUtNB2FiLKLD4zttATB73XGpkPcvicfMnSo7wBgQiWDUKh9aaeLsQywNVGBRW8aTF8Jh9PmwkCn6BF6b" } ]
"""

def get_client_path(search_paths, docker=None, network_config=None, verbose=None):
    client_exe = REGULAR_CLIENT_EXE
    if docker:
        client_exe = DOCKER_CLIENT_EXE.replace("%network%", network_config['NAME'].lower())
    for search_path in search_paths:
        expanded_path = os.path.expanduser(search_path)
        client_path = os.path.join(expanded_path, client_exe)
        if os.path.isfile(client_path):
            return client_path+DOCKER_CLIENT_EXE_SUFFIX if docker else client_path
        if verbose: print("Not found {}".format(client_path))

    raise Exception("Client executable not found. Review --executable_dirs, --docker and --network parameters")


def send_request(cmd, verbose=None):
    if verbose:
        print("Command is |{}|".format(cmd))

    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    bytes = []
    for b in process.stdout:
        bytes.append(b)

    process.wait()

    buffer = b''.join(bytes).decode('utf-8')

    if verbose:
        print("Answer is |{}|".format(buffer))

    return buffer


def check_response(response):
    print(response)
    if "Error:" in response or "error" in response or "invalid" in response or "Unexpected server answer" in response:
        return False
    return True

if __name__ == '__main__':
    print(check_response(test_str))

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
