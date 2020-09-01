import json

from log_config import main_logger

logger = main_logger


def extract_json_part(input, verbose=None):

    if verbose:
        logger.debug("->will parse json response_str is '{}'".format(input))

    # because of disclaimer header; find beginning of response
    idx = input.find("{")
    if idx < 0:
        idx = input.find("[")
    if idx < 0:
        idx = input.find("\"")

    if idx < 0:
        return None

    extracted_json_part = input[idx:].strip()

    if verbose:
        logger.debug("<-parsed json response_str is '{}'".format(extracted_json_part))

    return extracted_json_part


def parse_json_response(client_response, verbose=None):
    response_str = extract_json_part(client_response, verbose)

    if response_str is None:
        raise Exception("Unknown client response format")

    return json.loads(response_str)
