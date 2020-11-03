from conseil.api import ConseilApi
from conseil.core import ConseilClient
from time import sleep
import requests
from parse import parse
#from log_config import main_logger
#logger = main_logger

conseil = ConseilClient(ConseilApi(
    api_key='6c46dd91-b691-48f1-a204-511dd0158875',
    api_host='https://conseil-prod.cryptonomic-infra.tech:443',
    api_version=2
))
def getContractStorage_conseil(contract_id, snapshot_block):
    Account = conseil.tezos.mainnet.accounts_history
    query = Account.query(Account.storage).filter(Account.block_id <= snapshot_block, Account.account_id == contract_id)
    storage_data = query.all()[0]['storage']
    return parse_dexter_storage(storage_data)
def getLiquidityProvidersList_conseil(contract_id):
    listLPs = set([])
    Operations = conseil.tezos.mainnet.operations
    query = Operations.query().filter(Operations.destination == contract_id, Operations.parameters_entrypoints == 'addLiquidity')
    data = query.all()
    for item in data:
        listLPs.add(item['source'])
    return listLPs

def getContractStorage_rpc(contract_id, snapshot_block):
    uri = "https://mainnet-tezos.giganode.io/chains/main/blocks/{}/context/contracts/{}/storage".format(snapshot_block, contract_id)
    resp = requests.get(uri, timeout=5)
    storage_data = resp.json()
    return parse_dexter_storage(storage_data)
def getContractBalance_rpc(contract_id, snapshot_block):
    uri = "https://mainnet-tezos.giganode.io/chains/main/blocks/{}/context/contracts/{}/balance".format(snapshot_block, contract_id)
    resp = requests.get(uri, timeout=5)
    return resp.json()
def getCurrentBalance_rpc(acc):
    uri = "https://mainnet-tezos.giganode.io/chains/main/blocks/head/context/contracts/{}/balance".format(acc)
    resp = requests.get(uri, timeout=5)
    return int(resp.json())

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
def parse_dexter_storage(storage_input):
    storage = {}
    try: # Json map format
        storage['big_map_id'] = storage_input['args'][0]['int']

        storage['selfIsUpdatingTokenPool'] = storage_input['args'][1]['args'][0]['args'][0]['prim']

        storage['freezeBaker'] = storage_input['args'][1]['args'][0]['args'][1]['args'][0]['prim']
        storage['lqtTotal'] = storage_input['args'][1]['args'][0]['args'][1]['args'][1]['int']

        storage['manager'] = storage_input['args'][1]['args'][1]['args'][0]['args'][0]['string']
        storage['tokenAddress'] = storage_input['args'][1]['args'][1]['args'][0]['args'][1]['string']
        storage['tokenPool'] = storage_input['args'][1]['args'][1]['args'][1]['args'][0]['int']
        storage['xtzPool'] = storage_input['args'][1]['args'][1]['args'][1]['args'][0]['int']

        return storage

    except:
        try:
            data = parse('Pair {} (Pair (Pair {} (Pair {} {})) (Pair (Pair "{}" "{}") (Pair {} {})))', storage_input)
            storage_fields = ['big_map_id', 'selfIsUpdatingTokenPool', 'freezeBaker', 'lqtTotal', 'manager', 'tokenAddress',
                              'tokenPool', 'xtzPool']
            for i in range(len(storage_fields)):
                storage[storage_fields[i]] = data[i]
            return storage
        except:
            logger.warn('Parsing dexter storage not successful')
            return storage


def getLiquidityProvidersList_tzstats(big_map_id, snapshot_block):
    offset = 0
    listLPs = {}
    resp = ' '
    while resp != []:
        uri = f'http://api.tzstats.com/explorer/bigmap/{big_map_id}/values?limit=100&offset={offset}&block={snapshot_block}'
        offset += 100
        resp = requests.get(uri, timeout=5)
        if resp.status_code == 200:
            resp = resp.json()
            for item in resp:
                listLPs[item['key']] = int(item['value']['balance'])
    return listLPs

def getBalanceFromBigMap_rpc(big_map_id, LP_script_expr, snapshot_block):
    uri = "https://mainnet-tezos.giganode.io/chains/main/blocks/{}/context/big_maps/{}/{}".format(snapshot_block, big_map_id, LP_script_expr)
    for trial in range(3):
        resp = requests.get(uri, timeout=5)
        if resp.status_code == 200:
            sleep(0.5)
            return int(resp.json()['args'][0]['int'])
    return 0

def getBalanceFromBigMap_tzstats(big_map_id, LP_script_expr, snapshot_block):
    uri = f"https://api.tzstats.com/explorer/bigmap/{big_map_id}/{LP_script_expr}?block={snapshot_block}"
    for trial in range(3):
        resp = requests.get(uri, timeout=5)
        if resp.status_code == 200:
            sleep(0.5)
            return int(resp.json()['value']['balance'])
    return 0

def get_dexter_balance_map(contract_id = 'KT1Puc9St8wdNoGtLiD2WXaHbWU7styaxYhD', snapshot_block = 'BMQn5rnV1U5snTAmocdqzBgtGWd9kpUYnGHTh9zBhVWm5Mh5e5v'):
    print('\n\n')
    print(snapshot_block)
    print('\n\n')
    storage = getContractStorage_rpc(contract_id, snapshot_block)
    listLPs = getLiquidityProvidersList_tzstats(storage['big_map_id'], snapshot_block)
    listLPs_head = getLiquidityProvidersList_tzstats(storage['big_map_id'], 'head')
    balanceMap = {}
    for LP in listLPs:
        balanceMap[LP] = {}
        #liquidity_share = getBalanceFromBigMap_tzstats(storage['big_map_id'], listLPs[LP], snapshot_block)
        #liquidity_share_ = getBalanceFromBigMap_tzstats(storage['big_map_id'], LP, snapshot_block)
        #print(LP, liquidity_share, liquidity_share_, getBalanceFromBigMap_rpc(storage['big_map_id'], listLPs[LP], 'head'))
        current_liquidity = listLPs_head[LP] if LP in listLPs_head else 0
        print(LP, listLPs[LP], current_liquidity)
        balanceMap[LP]['liquidity_share'] = listLPs[LP]
        balanceMap[LP]['current_balance'] = getCurrentBalance_rpc(LP)
    return balanceMap, int(storage['lqtTotal'])

def process_original_delegators_map(delegator_map, contract_id, snapshot_block):
    url = 'https://api.tzstats.com/tables/op?cycle=294&sender=tz1acsihTQWHEnxxNz7EEsBDLMTztoZQE9SW&limit=1000&columns=receiver,volume'
    resp = requests.get(url, timeout=5)
    payouts = resp.json()
    for payout in payouts:
        addr = payout[0]
        if addr in delegator_map:
            print(addr, delegator_map[addr], payout[1])
        else:
            print(addr, payout[1])
    addresses = [x[0] for x in payouts]
    contract_balance = delegator_map[contract_id]['staking_balance']
    dexter_liquidity_provider_map, totalLiquidity = get_dexter_balance_map(contract_id, snapshot_block)
    del delegator_map[contract_id]
    sum_delegated_liquidity = 0
    print('\n\n')
    for delegator in dexter_liquidity_provider_map:
        balance = int(dexter_liquidity_provider_map[delegator]['liquidity_share'] * contract_balance / totalLiquidity)
        if delegator in delegator_map:
            delegator_map[delegator]['staking_balance'] += balance
        else:
            delegator_map[delegator] = {}
            delegator_map[delegator]['staking_balance'] = balance
            delegator_map[delegator]['current_balance'] = dexter_liquidity_provider_map[delegator]['current_balance']
        if delegator in addresses:
            print(delegator, delegator_map[delegator]['staking_balance'], payouts[addresses.index(delegator)])
        else:
            print(delegator, delegator_map[delegator]['staking_balance'])
        sum_delegated_liquidity += balance
    print(sum_delegated_liquidity, contract_balance)

def test_dexter_implementation(contract_id = 'KT1Puc9St8wdNoGtLiD2WXaHbWU7styaxYhD', snapshot_block = 'BMQn5rnV1U5snTAmocdqzBgtGWd9kpUYnGHTh9zBhVWm5Mh5e5v'):
    print('Start')
    storage = getContractStorage_rpc(contract_id, snapshot_block)
    print(storage)
    listLPs = getLiquidityProvidersList_tzstats(storage['big_map_id'])
    balanceMap = {}
    lqdt_ttl = 0
    for i, LP in enumerate(listLPs):
        print("{}/{}".format(i, len(listLPs)))
        balanceMap[LP] = getBalanceFromBigMap_rpc(storage['big_map_id'], listLPs[LP], snapshot_block)
        lqdt_ttl += balanceMap[LP]
    assert(lqdt_ttl == int(storage['lqtTotal']))

if __name__ == '__main__':
#    test_dexter_implementation()
    block_0 = 1149672
    schritt = 100
    contract_id = 'KT1Puc9St8wdNoGtLiD2WXaHbWU7styaxYhD'
    for block in range(block_0, block_0+schritt*1000, schritt):
        balance = getContractBalance_rpc(contract_id, block)
        storage = getContractStorage_rpc(contract_id, block)
        print(block, balance, storage['lqtTotal'])