from rpc.lrpc_reward_api import LRpcRewardApiImpl
from rpc.prpc_reward_api import PRpcRewardApiImpl
from rpc.rpc_block_api import RpcBlockApiImpl
from rpc.rpc_reward_api import RpcRewardApiImpl
from tzstats.tzstats_block_api import TzStatsBlockApiImpl
from tzstats.tzstats_reward_api import TzStatsRewardApiImpl

class ProviderFactory:
    URL = "{}.tezrpc.me"
    url_prefixes = {"MAINNET": "mainnet", "ALPHANET": "alphanet", "ZERONET": "zeronet"}

    def __init__(self, provider, verbose=False):
        self.provider = provider
        self.verbose = verbose

    def newRewardApi(self, network_config, baking_address, wllt_clnt_mngr, node_url):
        if self.provider == 'rpc':
            return LRpcRewardApiImpl(network_config, baking_address, node_url, wllt_clnt_mngr, validate=False, verbose=self.verbose)
        elif self.provider == 'prpc':
            url_prefix = self.url_prefixes[network_config['NAME']]
            return PRpcRewardApiImpl(network_config,  baking_address, self.URL.format(url_prefix), validate=False, verbose=self.verbose)
        elif self.provider == 'tzstats':
            return TzStatsRewardApiImpl(network_config, baking_address, verbose=self.verbose)
        raise Exception("No supported reward data provider : {}".format(self.provider))

    def newBlockApi(self, network_config, wllt_clnt_mngr, node_url):
        if self.provider == 'rpc' or self.provider == 'prpc':
            return RpcBlockApiImpl(network_config, wllt_clnt_mngr, node_url)
        elif self.provider == 'tzstats':
            return TzStatsBlockApiImpl(network_config)
        raise Exception("No supported reward data provider : {}".format(self.provider))
