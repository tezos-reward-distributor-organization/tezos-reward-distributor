from rpc.rpc_block_api import RpcBlockApiImpl
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzstats.tzstats_block_api import TzStatsBlockApiImpl
from tzstats.tzstats_reward_api import TzStatsRewardApiImpl
from tzkt.tzkt_block_api import TzKTBlockApiImpl
from tzkt.tzkt_reward_api import TzKTRewardApiImpl
from Constants import PUBLIC_NODE_URL


class ProviderFactory:
    def __init__(self, provider):
        self.provider = provider

    def newRewardApi(self, network_config, baking_address, node_url, node_url_public='', api_base_url=None):
        if self.provider == 'rpc':
            if node_url.find("http") == -1:
                node_url = 'http://' + node_url
            return RpcRewardApiImpl(network_config, baking_address, node_url)
        elif self.provider == 'prpc':
            if node_url_public == '':
                node_url_public = PUBLIC_NODE_URL[network_config['NAME']]
            return RpcRewardApiImpl(network_config, baking_address, node_url_public)
        elif self.provider == 'tzstats':
            return TzStatsRewardApiImpl(network_config, baking_address)
        elif self.provider == 'tzkt':
            return TzKTRewardApiImpl(network_config, baking_address, base_url=api_base_url)

        raise Exception("No supported reward data provider : {}".format(self.provider))

    def newBlockApi(self, network_config, node_url, api_base_url=None):
        if self.provider == 'rpc' or self.provider == 'prpc':
            if node_url.find("http") == -1:
                node_url = 'http://' + node_url
            return RpcBlockApiImpl(network_config, node_url)
        elif self.provider == 'tzstats':
            return TzStatsBlockApiImpl(network_config)
        elif self.provider == 'tzkt':
            return TzKTBlockApiImpl(network_config, base_url=api_base_url)

        raise Exception("No supported reward data provider : {}".format(self.provider))
