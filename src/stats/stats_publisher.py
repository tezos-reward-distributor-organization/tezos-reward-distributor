import json
import requests
from log_config import main_logger
from platform import platform
from sys import version_info

url = "https://jptpfltc1k.execute-api.us-west-2.amazonaws.com/trdstats"

logger = main_logger


def stats_publisher(stats_dict):

    logger.info("Sending anonymous statistics; See docs/statistics.rst for more information.")

    try:
        stats_dict['pythonver'] = "{}.{}".format(version_info.major, version_info.minor)
        stats_dict['os'] = platform()

        stats_txt = json.dumps(stats_dict)
        logger.debug("stats_publish data: {}".format(stats_txt))

        resp = requests.post(url, data=stats_txt, timeout=5)
        if resp.status_code != 200:
            raise Exception("Unable to POST anonymous stats: {}".format(resp.text))

    except Exception as e:
        logger.error("stats_publish Error: {}".format(e))

    return
