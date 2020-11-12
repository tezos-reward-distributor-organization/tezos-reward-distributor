from time import sleep
import requests
from parse import parse

from log_config import main_logger
logger = main_logger


def get_dexter_balance_map(contract_id, snapshot_block, api_provider):
    big_map_id = api_provider.get_big_map_id(contract_id)
    listLPs = api_provider.get_liquidity_providers_list(big_map_id, snapshot_block)
    balanceMap = {}
    totalLiquidity = 0
    for LP in listLPs:
        balanceMap[LP] = {'liquidity_share': listLPs[LP]}
        totalLiquidity += listLPs[LP]
    api_provider.update_current_balances_dexter(balanceMap)
    return balanceMap, totalLiquidity


def process_original_delegators_map(delegator_map, contract_id, snapshot_block, api_provider):

    contract_balance = delegator_map[contract_id]['staking_balance']
    dexter_liquidity_provider_map, totalLiquidity = get_dexter_balance_map(contract_id, snapshot_block, api_provider)

    del delegator_map[contract_id]

    for delegator in dexter_liquidity_provider_map:
        balance = int(dexter_liquidity_provider_map[delegator]['liquidity_share'] * contract_balance / totalLiquidity)
        if delegator in delegator_map:
            delegator_map[delegator]['staking_balance'] += balance
        else:
            delegator_map[delegator] = {}
            delegator_map[delegator]['staking_balance'] = balance
            delegator_map[delegator]['current_balance'] = dexter_liquidity_provider_map[delegator]['current_balance']

    # url = 'https://api.tzstats.com/tables/op?hash=onydXMUCP5JFQp19VfFk6WJ54LftNxo3a34sw1uE3CbbxhmMNw3&limit=1000&columns=receiver,volume'
    # resp = requests.get(url, timeout=5)
    # payouts = resp.json()
    # for payout in payouts:
    #    addr = payout[0]
    #    if (addr in dexter_liquidity_provider_map) and (dexter_liquidity_provider_map[addr]['liquidity_share'] != 0):
    #        print(addr, payout[1], payout[1] / (dexter_liquidity_provider_map[addr]['liquidity_share'] / totalLiquidity))
    #    else:
    #        print(addr, payout[1])
    # print(sum_delegated_liquidity, contract_balance)


def parse_dexter_storage(storage_input):
    '''
    Dexter Exchange Contract represents a liquidity pool contract and has the following form
    storage (pair (big_map %accounts (address :owner)
                                 (pair (nat :balance)
                                       (map (address :spender)
                                            (nat :allowance))))
              (pair (pair (bool :selfIsUpdatingTokenPool)
                          (pair (bool :freezeBaker)
                                (nat :lqtTotal)))
                    (pair (pair (address :manager)
                                (address :tokenAddress))
                          (pair (nat :tokenPool)
                                (mutez :xtzPool)))));
    '''
    storage = {}
    try:  # Json map format
        storage['big_map_id'] = storage_input['args'][0]['int']

        storage['selfIsUpdatingTokenPool'] = storage_input['args'][1]['args'][0]['args'][0]['prim']

        storage['freezeBaker'] = storage_input['args'][1]['args'][0]['args'][1]['args'][0]['prim']
        storage['lqtTotal'] = storage_input['args'][1]['args'][0]['args'][1]['args'][1]['int']

        storage['manager'] = storage_input['args'][1]['args'][1]['args'][0]['args'][0]['string']
        storage['tokenAddress'] = storage_input['args'][1]['args'][1]['args'][0]['args'][1]['string']
        storage['tokenPool'] = storage_input['args'][1]['args'][1]['args'][1]['args'][0]['int']
        storage['xtzPool'] = storage_input['args'][1]['args'][1]['args'][1]['args'][0]['int']

        return storage

    except Exception:
        try:  # storage through rpc query
            data = parse('Pair {} (Pair (Pair {} (Pair {} {})) (Pair (Pair "{}" "{}") (Pair {} {})))', storage_input)
            storage_fields = ['big_map_id', 'selfIsUpdatingTokenPool', 'freezeBaker', 'lqtTotal', 'manager', 'tokenAddress',
                              'tokenPool', 'xtzPool']
            for i in range(len(storage_fields)):
                storage[storage_fields[i]] = data[i]
            return storage
        except Exception:
            logger.warn('Parsing dexter storage not successful')
            return storage


# def test_dexter_implementation(contract_id = 'KT1Puc9St8wdNoGtLiD2WXaHbWU7styaxYhD', snapshot_block = 'BMQn5rnV1U5snTAmocdqzBgtGWd9kpUYnGHTh9zBhVWm5Mh5e5v'):
#     storage = getContractStorage_rpc(contract_id, snapshot_block)
#     listLPs = getLiquidityProvidersList_tzstats(storage['big_map_id'])
#     balanceMap = {}
#     lqdt_ttl = 0
#     for i, LP in enumerate(listLPs):
#         print("{}/{}".format(i, len(listLPs)))
#         balanceMap[LP] = getBalanceFromBigMap_rpc(storage['big_map_id'], listLPs[LP], snapshot_block)
#         lqdt_ttl += balanceMap[LP]
#     assert(lqdt_ttl == int(storage['lqtTotal']))
