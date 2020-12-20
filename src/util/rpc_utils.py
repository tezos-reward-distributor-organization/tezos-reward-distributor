import re
import json

from log_config import main_logger, verbose_logger

logger = main_logger


def extract_json_part(input):
    verbose_logger.debug("->will parse json response_str is '{}'".format(input))

    # because of disclaimer header; find beginning of response
    idx = input.find("{")
    if idx < 0:
        idx = input.find("[")
    if idx < 0:
        idx = input.find("\"")

    if idx < 0:
        return None

    extracted_json_part = input[idx:].strip()

    verbose_logger.debug("<-parsed json response_str is '{}'".format(extracted_json_part))

    return extracted_json_part


def parse_json_response(client_response):
    response_str = extract_json_part(client_response)

    if response_str is None:
        # Unable to parse JSON; look for some common error messages

        # Catch 'Counter 823645 already used for contract' error
        counter_used_re = re.compile(r"Counter (\d+) already used.*expected (\d+)")
        counter_match = counter_used_re.match(client_response)
        if counter_match:
            raise Exception("Transaction counter mismatch ({:d}/{:d})"
                            .format(counter_match.group(1), counter_match.group(2)))

        # TODO Add more as discovered

        # else, generic error on parsing response
        raise Exception("Unknown client response format")

    return json.loads(response_str)
