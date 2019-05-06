import json

from util.client_utils import clear_terminal_chars


def parse_json_response(client_response, verbose=None):
    client_response = clear_terminal_chars(client_response)

    if verbose:
        print("will parse json response_str is '{}'".format(client_response))

    # because of disclaimer header; find beginning of response
    idx = client_response.find("{")
    if idx < 0:
        idx = client_response.find("[")
    if idx < 0:
        idx = client_response.find("\"")
    if idx < 0:
        raise Exception("Unknown client response format")

    response_str = client_response[idx:].strip()
    if verbose:
        print("parsed json response_str is '{}'".format(response_str))

    return json.loads(response_str)
