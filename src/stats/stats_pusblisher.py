import json
import threading
import requests
from time import sleep
from Constants import VERSION

url = "http://35.211.164.111:8080/trd/stats/add"
headers = {'content-type': 'application/json'}


def stat_publish(stats_map):
    t = threading.Thread(target=stat_publish_job, name="stat_publish_job", args=({'stats':stats_map},))
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
    stats_dict['trdversion'] = VERSION

    stat_publish(stats_dict)

    sleep(1)
