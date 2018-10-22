import requests

from BlockApi import BlockApi

API = {'MAIN': {'HEAD_API_URL': 'https://api6.tzscan.io/v2/head'},
       'ALPHA': {'HEAD_API_URL': 'http://alphanet-api.tzscan.io/v2/head'},
       'ZERO': {'HEAD_API_URL': 'http://zeronet-api.tzscan.io/v2/head'}
       }

class TzScanBlockApi(BlockApi):

    def __init__(self,nw):
        super().__init__(nw)

        self.api = API[nw['NAME']]
        if self.api is None:
            raise Exception("Unknown network {}".format(nw))



    def get_current_level(self):
        resp = requests.get(self.api['HEAD_API_URL'])
        if resp.status_code != 200:
            # This means something went wrong.
            raise Exception('GET /head/ {}'.format(resp.status_code))
        root = resp.json()
        current_level = int(root["level"])

        return current_level


