import requests
from log_config import main_logger
from platform import platform
from sys import version_info

STATS_URL = "https://jptpfltc1k.execute-api.us-west-2.amazonaws.com/trdstats"

logger = main_logger


def stats_publisher(stats_dict):

    logger.info("Sending anonymous statistics; See docs/statistics.rst for more information.")

    try:
        stats_dict['pythonver'] = "{}.{}".format(version_info.major, version_info.minor)
        stats_dict['os'] = platform()

        logger.debug("stats_publisher data: {}".format(stats_dict))

        resp = requests.post(STATS_URL, json=stats_dict, timeout=15, headers={'user-agent': 'trd/0.0.1'})
        if resp.status_code != 200:
            raise Exception("Unable to POST anonymous stats: {}".format(resp.text))

    except Exception as e:
        logger.error("stats_publish Error: {}".format(str(e)))

    return
