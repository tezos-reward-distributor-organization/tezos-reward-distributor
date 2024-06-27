from tzkt.tzkt_block_api import TzKTBlockApiImpl
from tzkt.tzkt_reward_api import TzKTRewardApiImpl

class ProviderFactory:
    def __init__(self, provider):
        self.provider = provider

    def newRewardApi(
        self,
        network_config,
        baking_address,
        node_url,
        node_url_public="",
        api_base_url=None,
        tzpro_api_key="",
    ):
        return TzKTRewardApiImpl(
            network_config, baking_address, base_url=api_base_url
        )

    def newBlockApi(
        self,
        network_config,
        node_url,
        api_base_url=None,
        tzpro_api_key="",
    ):
        return TzKTBlockApiImpl(network_config, base_url=api_base_url)
