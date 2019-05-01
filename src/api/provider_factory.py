from rpc.rpc_block_api import RpcBlockApiImpl
from rpc.rpc_reward_api import RpcRewardApiImpl
from rpc.rpc_reward_calculator import RpcRewardCalculatorApi
from tzscan.mirror_selection_helper import TzScanMirrorSelector
from tzscan.tzscan_block_api import TzScanBlockApiImpl
from tzscan.tzscan_reward_api import TzScanRewardApiImpl
from tzscan.tzscan_reward_calculator import TzScanRewardCalculatorApi


class ProviderFactory:

    def __init__(self, provider):
        self.provider = provider
        self.mirror_selector = None

    def newRewardApi(self, network_config, baking_address, wllt_clnt_mngr, node_url):
        if self.provider == 'rpc':
            return RpcRewardApiImpl(network_config, baking_address, wllt_clnt_mngr, node_url)
        elif self.provider == 'tzscan':
            if not self.mirror_selector:
                self.init_mirror_selector(network_config)
            return TzScanRewardApiImpl(network_config, baking_address, self.mirror_selector)

        raise Exception("No supported reward data provider : {}".format(self.provider))

    def init_mirror_selector(self, network_config):
        self.mirror_selector = TzScanMirrorSelector(network_config)
        self.mirror_selector.initialize()

    def newBlockApi(self, network_config, wllt_clnt_mngr, node_url):
        if self.provider == 'rpc':
            return RpcBlockApiImpl(network_config, wllt_clnt_mngr, node_url)
        elif self.provider == 'tzscan':
            if not self.mirror_selector:
                self.init_mirror_selector(network_config)
            return TzScanBlockApiImpl(network_config, self.mirror_selector)

        raise Exception("No supported reward data provider : {}".format(self.provider))

    def newCalcApi(self, founders_map, min_delegation_amt, excluded_delegators_set, rc):
        if self.provider == 'rpc':
            return RpcRewardCalculatorApi(founders_map, min_delegation_amt, excluded_delegators_set, rc)
        elif self.provider == 'tzscan':
            return TzScanRewardCalculatorApi(founders_map, min_delegation_amt, excluded_delegators_set, rc)

        raise Exception("No supported reward data provider : {}".format(self.provider))
