import json
from time import sleep

import requests
import threading
import time
import datetime

import version

url = "http://34.74.27.213:8080/trd/stats/add"
headers = {'content-type': 'application/json'}


def stat_publish(stats_map):
    stats_map['time_zone'] = time.timezone / -(60 * 60)  # e.g. +3
    stats_map['time'] = str(datetime.datetime.now())  # e.g. '2017-03-12 22:29:03.066794'

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
    stats_dict['nb_failed'] = 0
    stats_dict['nb_founder'] = 1
    stats_dict['nb_owner'] = 1
    stats_dict['nb_delegator'] = 10
    stats_dict['cycle'] = 83
    stats_dict['delegator_pays_fee'] = 1
    stats_dict['trdversion'] = version

    stat_publish(stats_dict)

    sleep(1)
