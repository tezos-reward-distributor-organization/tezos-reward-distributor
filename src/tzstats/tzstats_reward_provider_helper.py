import requests

from time import sleep
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger
from tzstats.tzstats_api_constants import *

logger = main_logger

rewards_split_call = '/tables/income?address={}&cycle={}'
delegators_call = '/tables/snapshot?cycle={}&is_selected=1&delegate={}&columns=balance,delegated,address&limit=50000'

batch_current_balance_call = '/tables/account?delegate={}&columns=row_id,spendable_balance,address&limit=50000'
single_current_balance_call = '/tables/account?address.in={}&columns=row_id,spendable_balance,address'
snapshot_cycle = '/explorer/cycle/{}'

contract_storage = '/explorer/contract/{}/storage'
balance_LP_call = '/explorer/bigmap/{}/values?limit=100&offset={}&block={}'

PREFIX_API = {
    'MAINNET': {'API_URL': 'http://api.tzstats.com'},
    'ZERONET': {'API_URL': 'http://api.zeronet.tzstats.com'},
    'ALPHANET': {'API_URL': 'http://api.carthagenet.tzstats.com'}
}


def split(input, n):
    for i in range(0, len(input), n):
        yield input[i:i + n]


class TzStatsRewardProviderHelper:

    def __init__(self, nw, baking_address):
        super(TzStatsRewardProviderHelper, self).__init__()

        self.preserved_cycles = nw['NB_FREEZE_CYCLE']

        self.api = PREFIX_API[nw['NAME']]
        if self.api is None:
            raise ApiProviderException("Unknown network {}".format(nw))

        self.baking_address = baking_address

    def get_rewards_for_cycle(self, cycle, expected_reward=False):

        root = {"delegate_staking_balance": 0, "total_reward_amount": 0, "delegators_balances": {}}

        #
        # Get rewards breakdown for cycle
        #
        uri = self.api['API_URL'] + rewards_split_call.format(self.baking_address, cycle)

        sleep(0.5)  # be nice to tzstats

        verbose_logger.debug("Requesting rewards breakdown, {}".format(uri))

        resp = requests.get(uri, timeout=5)

        verbose_logger.debug("Response from tzstats is {}".format(resp.content.decode("utf8")))

        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()[0]
        if expected_reward:
            root["total_reward_amount"] = int(1e6 * float(resp[idx_income_expected_income]))
        else:
            root["total_reward_amount"] = int(1e6 * (float(resp[idx_income_baking_income])
                                                     + float(resp[idx_income_endorsing_income])
                                                     + float(resp[idx_income_seed_income])
                                                     + float(resp[idx_income_fees_income])
                                                     - float(resp[idx_income_lost_accusation_fees])
                                                     - float(resp[idx_income_lost_accusation_rewards])
                                                     - float(resp[idx_income_lost_revelation_fees])
                                                     - float(resp[idx_income_lost_revelation_rewards])))

        #
        # Get staking balances of delegators at snapshot block
        #
        uri = self.api['API_URL'] + delegators_call.format(cycle - self.preserved_cycles - 2, self.baking_address)

        sleep(0.5)  # be nice to tzstats

        verbose_logger.debug("Requesting staking balances of delegators, {}".format(uri))

        resp = requests.get(uri, timeout=5)

        verbose_logger.debug("Response from tzstats is {}".format(resp.content.decode("utf8")))

        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()

        for delegator in resp:

            if delegator[idx_delegator_address] == self.baking_address:
                root["delegate_staking_balance"] = int(1e6 * (float(delegator[idx_balance]) + float(delegator[idx_baker_delegated])))
            else:
                delegator_info = {"staking_balance": 0, "current_balance": 0}
                delegator_info["staking_balance"] = int(1e6 * float(delegator[idx_balance]))
                root["delegators_balances"][delegator[idx_delegator_address]] = delegator_info

        #
        # Get current balance of delegates
        #
        # This is done in 2 phases. 1) make a single API call to tzstats, retrieving an array
        # of arrays with current balance of each delegator who "currently" delegates to delegate. There may
        # be a case where the delegator has changed delegations and would therefor not be in this array.
        # Thus, 2) determines which delegators are not in the first result, and makes individual
        # calls to get their balance. This approach should reduce the overall number of API calls made to tzstats.
        #

        # Phase 1
        #
        uri = self.api['API_URL'] + batch_current_balance_call.format(self.baking_address)

        sleep(0.5)  # be nice to tzstats

        verbose_logger.debug("Requesting current balance of delegators, phase 1, {}".format(uri))

        resp = requests.get(uri, timeout=5)

        verbose_logger.debug("Response from tzstats is {}".format(resp.content.decode("utf8")))

        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()

        # Will use these two lists to determine who has/has not been fetched
        staked_bal_delegators = root["delegators_balances"].keys()
        curr_bal_delegators = []

        for delegator in resp:
            delegator_addr = delegator[idx_cb_delegator_address]

            # If delegator is in this batch, but has no staking balance for this reward cycle,
            # then they must be a new delegator and are not receiving rewards at this time.
            # We can ignore them.
            if delegator_addr not in staked_bal_delegators:
                continue

            root["delegators_balances"][delegator_addr]["current_balance"] = int(1e6 * float(delegator[idx_cb_current_balance]))
            curr_bal_delegators.append(delegator_addr)

        # Phase 2
        #

        # Who was not in this result?
        need_curr_balance_fetch = list(set(staked_bal_delegators) - set(curr_bal_delegators))

        # Fetch individual not in original batch
        if len(need_curr_balance_fetch) > 0:
            split_addresses = split(need_curr_balance_fetch, 50)
            for list_address in split_addresses:
                list_curr_balances = self.__fetch_current_balance(list_address)
                for d in list_address:
                    root["delegators_balances"][d]["current_balance"] = list_curr_balances[d]
                    curr_bal_delegators.append(d)

        # All done fetching balances.
        # Sanity check.
        n_curr_balance = len(curr_bal_delegators)
        n_stake_balance = len(staked_bal_delegators)

        if n_curr_balance != n_stake_balance:
            raise ApiProviderException('Did not fetch all balances {}/{}'.format(n_curr_balance, n_stake_balance))

        return root

    def update_current_balances(self, reward_logs):
        """External helper for fetching current balance of addresses"""
        for rl in reward_logs:
            rl.current_balance = self.__fetch_current_balance([rl.address])[rl.address]

    def get_snapshot_level(self, cycle):

        uri = self.api['API_URL'] + snapshot_cycle.format(cycle)

        resp = requests.get(uri, timeout=5)

        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

        snapshot_height = resp.json()['snapshot_cycle']['snapshot_height']
        return snapshot_height

    def __fetch_current_balance(self, address_list):
        param_txt = ''
        for address in address_list:
            param_txt += address + ','
        param_txt = param_txt[:-1]
        uri = self.api['API_URL'] + single_current_balance_call.format(param_txt)

        sleep(0.5)  # be nice to tzstats

        verbose_logger.debug("Requesting current balance of delegator, phase 2, {}".format(uri))

        resp = requests.get(uri, timeout=5)

        verbose_logger.debug("Response from tzstats is {}".format(resp.content.decode("utf8")))

        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()

        ret_list = {}
        for item in resp:
            ret_list[item[idx_cb_delegator_address]] = int(1e6 * float(item[idx_cb_current_balance]))

        return ret_list

    def get_big_map_id(self, contract_id):
        uri = self.api['API_URL'] + contract_storage.format(contract_id)

        verbose_logger.debug("Requesting contract storage, {}".format(uri))

        resp = requests.get(uri, timeout=5)

        verbose_logger.debug("Response from tzstats is {}".format(resp.content.decode("utf8")))

        if resp.status_code != 200:
            # This means something went wrong.
            raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

        resp = resp.json()

        return resp['value']['accounts']

    def get_liquidity_providers_list(self, big_map_id, snapshot_block):
        offset = 0
        listLPs = {}
        resp = ' '
        while resp != []:
            uri = self.api['API_URL'] + balance_LP_call.format(big_map_id, offset, snapshot_block)
            offset += 100

            verbose_logger.debug("Requesting LP balances, {}".format(uri))

            resp = requests.get(uri, timeout=5)

            verbose_logger.debug("Response from tzstats is {}".format(resp.content.decode("utf8")))

            if resp.status_code != 200:
                # This means something went wrong.
                raise ApiProviderException('GET {} {}'.format(uri, resp.status_code))

            resp = resp.json()
            for item in resp:
                listLPs[item['key']] = int(item['value']['balance'])

        return listLPs

    def update_current_balances_dexter(self, balanceMap):
        split_addresses = split(list(balanceMap.keys()), 50)
        for list_address in split_addresses:
            list_curr_balances = self.__fetch_current_balance(list_address)
            for d in list_address:
                balanceMap[d].update({"current_balance": list_curr_balances[d]})
