import json
import threading
import requests
import version
from time import sleep

url = "https://jptpfltc1k.execute-api.us-west-2.amazonaws.com/default/TRDStats"
headers = {'content-type': 'application/json'}


def stat_publish(stats_map):
    t = threading.Thread(target=stat_publish_job, name="stat_publish_job", args=({'stats': stats_map},))
    t.daemon = True
    t.start()


def stat_publish_job(stats_map):
    try:
        stats_txt = json.dumps(stats_map)
        requests.post(url, data=stats_txt, headers=headers)
    except Exception:
        pass


if __name__ == '__main__':
    stats_dict = {}
    stats_dict['total_amount'] = 123
    stats_dict['nb_payments'] = 12
    stats_dict['trdversion'] = version

    stat_publish(stats_dict)

    sleep(1)
