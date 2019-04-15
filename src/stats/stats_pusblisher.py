import json
import requests
import threading

url = "http://172.30.10.8:8080/trd/stats/"
headers = {'content-type': 'application/json'}


def stat_publish(stats_map):
    t = threading.Thread(target=stat_publish_job, name="stat_publish_job", args=(stats_map,))
    t.daemon = True
    t.start()

def stat_publish_job(stats_map):
    try:
        stats_txt = json.dumps(stats_map)
        requests.post(url, data=stats_txt, headers=headers)
    except Exception:
        pass


if __name__ == '__main__':
    stat_publish({"a":"b","c":"d"})