from rpc.rpc_block_api import RpcBlockApiImpl
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzscan.tzscan_block_api import TzScanBlockApiImpl
from tzscan.tzscan_reward_api import TzScanRewardApiImpl

class ProviderFactory:

    def __init__(self, provider):
        self.provider = provider

    def newRewardApi(self, network_config, baking_address, wllt_clnt_mngr, node_url):
        if self.provider == 'rpc':
            return RpcRewardApiImpl(network_config, baking_address, wllt_clnt_mngr, node_url)
        elif self.provider == 'tzscan':
            return TzScanRewardApiImpl(network_config, baking_address)

        raise Exception("No supported reward data provider : {}".format(self.provider))

    def newBlockApi(self, network_config, wllt_clnt_mngr, node_url):
        if self.provider == 'rpc':
            return RpcBlockApiImpl(network_config, wllt_clnt_mngr, node_url)
        elif self.provider == 'tzscan':
            return TzScanBlockApiImpl(network_config)

        raise Exception("No supported reward data provider : {}".format(self.provider))
