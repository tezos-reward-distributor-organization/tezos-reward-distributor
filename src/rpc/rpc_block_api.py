from api.block_api import BlockApi
from util.rpc_utils import parse_json_response

COMM_HEAD = " rpc get http://{}/chains/main/blocks/head"
COMM_REVELATION = " rpc get http://{}/chains/main/blocks/head/context/contracts/{}/manager_key"

class RpcBlockApiImpl(BlockApi):

    def __init__(self, nw, wllt_clnt_mngr, node_url):
        super(RpcBlockApiImpl, self).__init__(nw)
        
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.node_url = node_url
        
    def get_current_level(self, verbose=False):
        _, response = self.wllt_clnt_mngr.send_request(COMM_HEAD.format(self.node_url))
        head = parse_json_response(response)
        current_level = int(head["metadata"]["level"]["level"])
        return current_level

    def get_revelation(self, pkh, verbose=False):
        _, response = self.wllt_clnt_mngr.send_request(COMM_REVELATION.format(self.node_url, pkh))
        manager_key = parse_json_response(response, verbose=verbose)
        bool_revelation = "key" in manager_key.keys() and len(manager_key["key"]) > 0
        return bool_revelation



from cli.wallet_client_manager import WalletClientManager

def test_get_revelation():
    
    wllt_clnt_mngr = WalletClientManager("~/tezos-alpha/tezos-client", "", "", "", True)

    address_api = RpcBlockApiImpl({"NAME":"ALPHANET"}, wllt_clnt_mngr, "127.0.0.1:8732")
    print(address_api.get_revelation("tz1N5cvoGZFNYWBp2NbCWhaRXuLQf6e1gZrv"))
    print(address_api.get_revelation("KT1FXQjnbdqDdKNpjeM6o8PF1w8Rn2j8BmmG"))
    print(address_api.get_revelation("tz1YVxe7FFisREKXWNxdrrwqvw3o2jeXzaNb"))
