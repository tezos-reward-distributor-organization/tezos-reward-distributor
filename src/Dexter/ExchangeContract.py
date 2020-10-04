from conseil.api import ConseilApi
from conseil.core import ConseilClient

conseil = ConseilClient(ConseilApi(
    api_key='6c46dd91-b691-48f1-a204-511dd0158875',
    api_host='https://conseil-prod.cryptonomic-infra.tech:443',
    api_version=2
))
from parse import parse

# TODO: WIP
class ExchangeContract:

    def __init__(self, contract_id, snapshot_block):
        # self.contract_id = contract_id
        self.contract_id = "KT1Puc9St8wdNoGtLiD2WXaHbWU7styaxYhD"
        self.snapshot_block = snapshot_block

        self.conseil_client = conseil
        self.storage = {}

    def getLiquidityProvidersRewards(self):
        # get contract storage at snapshot block (snapshot block, contract_id)
        # get Liquidity Providers List
        # For each LP get balance from big map
        return 0


# ExchangeContractV1 represents a liquidity pool contract
# storage (pair (big_map %accounts (address :owner)
#                                  (pair (nat :balance)
#                                        (map (address :spender)
#                                             (nat :allowance))))
#               (pair (pair (bool :selfIsUpdatingTokenPool)
#                           (pair (bool :freezeBaker)
#                                 (nat :lqtTotal)))
#                     (pair (pair (address :manager)
#                                 (address :tokenAddress))
#                           (pair (nat :tokenPool)
#                                 (mutez :xtzPool)))));
    def getContractStorage(self):
        Account = self.conseil_client.tezos.mainnet.accounts
        query = Account.query(Account.storage).filter(Account.account_id == self.contract_id)
        data = parse('storage\nPair {} (Pair (Pair {} (Pair {} {})) (Pair (Pair "{}" "{}") (Pair {} {})))', query.all(output='csv'))
        storage_fields = ['big_map_id', 'selfIsUpdatingTokenPool', 'freezeBaker', 'lqtTotal', 'manager', 'tokenAddress',
                          'tokenPool', 'xtzPool']
        for i in range(len(storage_fields)):
            self.storage[storage_fields[i]] = data[i]


# Only for testing purposes
# WIP
if __name__ == '__main__':
    c = ExchangeContract()
    c.getContractStorage()
