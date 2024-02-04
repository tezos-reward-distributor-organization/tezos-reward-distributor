import requests
from http import HTTPStatus
from time import sleep

from exception.api_provider import ApiProviderException

from log_config import main_logger, verbose_logger
from blockwatch.tzpro_api_constants import (
    idx_income_baking_rights,
    idx_income_expected_income,
    idx_income_total_income,
    idx_income_lost_accusation_fees,
    idx_income_lost_accusation_rewards,
    idx_cb_delegator_address,
    idx_cb_current_balance,
    idx_income_active_stake,
    idx_income_lost_accusation_deposits,
    idx_income_lost_seed_fees,
    idx_income_lost_seed_rewards,
)
from Constants import TZPRO_API_URL, MUTEZ_PER_TEZ

logger = main_logger

rewards_split_call = "/tables/income?address={}&cycle={}"

reward_snapshot = "/explorer/bakers/{}/snapshot/{}"

delegators_call = "/tables/snapshot?cycle={}&is_selected=1&baker={}&columns=balance,delegated,address&limit=50000"

batch_current_balance_call = (
    "/tables/account?baker={}&columns=row_id,spendable_balance,address&limit=50000"
)
single_current_balance_call = (
    "/tables/account?address.in={}&columns=row_id,spendable_balance,address"
)
snapshot_cycle = "/explorer/cycle/{}"

contract_storage = "/explorer/contract/{}/storage"

balance_LP_call = "/explorer/bigmap/{}/values?limit=100&offset={}&block={}"

tip = "/explorer/tip"


def split(input, n):
    for i in range(0, len(input), n):
        yield input[i : i + n]


class TzProRewardProviderHelper:
    def __init__(self, nw, baking_address, key):
        super(TzProRewardProviderHelper, self).__init__()

        self.key = key

        self.api = TZPRO_API_URL[nw["NAME"]]
        if self.api is None:
            raise ApiProviderException("Unknown network {}".format(nw))

        self.baking_address = baking_address

    def get_rewards_for_cycle(self, cycle):
        root = {
            "delegate_staking_balance": 0,
            "num_baking_rights": 0,
            "potential_endorsement_rewards": 0,
            "rewards_and_fees": 0,
            "equivocation_losses": 0,
            "offline_losses": 0,
            "delegators_balances": {},
        }

        #
        # Get rewards breakdown for cycle
        #
        uri = self.api + rewards_split_call.format(self.baking_address, cycle)

        sleep(0.5)  # be nice to tzpro

        verbose_logger.debug("Requesting rewards breakdown, {}".format(uri))

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        verbose_logger.debug(
            "Response from tzpro is {}".format(resp.content.decode("utf8"))
        )

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

        resp = resp.json()[0]

        root["num_baking_rights"] = resp[idx_income_baking_rights]
        root["active_stake"] = resp[idx_income_active_stake]

        # rewards earned (excluding equivocation losses and equivocation accusation income)
        root["rewards_and_fees"] = int(
            MUTEZ_PER_TEZ * (float(resp[idx_income_total_income]))
        )
        # losses due to baker double baking, double endorsing or missing nonce
        root["equivocation_losses"] = int(
            MUTEZ_PER_TEZ
            * (
                float(resp[idx_income_lost_accusation_fees])
                + float(resp[idx_income_lost_accusation_rewards])
                + float(resp[idx_income_lost_accusation_deposits])
                + float(resp[idx_income_lost_seed_fees])
                + float(resp[idx_income_lost_seed_rewards])
            )
        )
        # TODO: Find out how to calculate denuciation rewards via tzpro
        root["denunciation_rewards"] = int(
            MUTEZ_PER_TEZ
            * (
                0
                # float(resp[idx_income_double_baking_income])
                # + float(resp[idx_income_double_endorsing_income])
            )
        )
        # losses due to being offline or not having enough bond
        root["offline_losses"] = int(
            MUTEZ_PER_TEZ
            * (
                float(resp[idx_income_expected_income])
                - float(resp[idx_income_total_income])
            )
        )

        # Get staking balances of delegators at snapshot block
        #
        uri = self.api + reward_snapshot.format(self.baking_address, cycle)
        sleep(0.5)  # be nice to tzpro

        verbose_logger.debug(
            "Requesting staking balances of delegators, {}".format(uri)
        )

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        verbose_logger.debug(
            "Response from tzpro is {}".format(resp.content.decode("utf8"))
        )

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

        resp = resp.json()

        root["delegate_staking_balance"] = int(resp["staking_balance"])
        for delegator in resp["delegators"]:
            delegator_info = {"staking_balance": 0, "current_balance": 0}
            delegator_info["staking_balance"] = int(delegator["balance"])
            if delegator_info["staking_balance"] > 0:
                root["delegators_balances"][delegator["address"]] = delegator_info

        #
        # Get current balance of delegates
        #
        # This is done in 2 phases. 1) make a single API call to tzpro, retrieving an array
        # of arrays with current balance of each delegator who "currently" delegates to delegate. There may
        # be a case where the delegator has changed delegations and would therefor not be in this array.
        # Thus, 2) determines which delegators are not in the first result, and makes individual
        # calls to get their balance. This approach should reduce the overall number of API calls made to tzpro.
        #

        # Phase 1
        #
        uri = self.api + batch_current_balance_call.format(self.baking_address)

        sleep(0.5)  # be nice to tzpro

        verbose_logger.debug(
            "Requesting current balance of delegators, phase 1, {}".format(uri)
        )

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        verbose_logger.debug(
            "Response from tzpro is {}".format(resp.content.decode("utf8"))
        )

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

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

            root["delegators_balances"][delegator_addr]["current_balance"] = int(
                MUTEZ_PER_TEZ * float(delegator[idx_cb_current_balance])
            )
            curr_bal_delegators.append(delegator_addr)

        # Phase 2
        #

        # Who was not in this result?
        need_curr_balance_fetch = list(
            set(staked_bal_delegators) - set(curr_bal_delegators)
        )

        # Fetch individual not in original batch
        if len(need_curr_balance_fetch) > 0:
            split_addresses = split(need_curr_balance_fetch, 50)
            for list_address in split_addresses:
                list_curr_balances = self.fetch_current_balance(list_address)
                for d in list_address:
                    root["delegators_balances"][d][
                        "current_balance"
                    ] = list_curr_balances[d]
                    curr_bal_delegators.append(d)

        # All done fetching balances.
        # Sanity check.
        n_curr_balance = len(curr_bal_delegators)
        n_stake_balance = len(staked_bal_delegators)

        if n_curr_balance != n_stake_balance:
            raise ApiProviderException(
                "Did not fetch all balances {}/{}".format(
                    n_curr_balance, n_stake_balance
                )
            )

        return root

    def update_current_balances(self, reward_logs):
        """External helper for fetching current balance of addresses"""
        split_addresses = split(reward_logs, 50)
        for list_address in split_addresses:
            addresses = [x.address for x in list_address]
            list_curr_balances = self.fetch_current_balance(addresses)
            for d in list_address:
                d.current_balance = list_curr_balances[d.address]

    def get_snapshot_level(self, cycle):
        uri = self.api + snapshot_cycle.format(cycle)

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

        snapshot_height = resp.json()["snapshot_cycle"]["snapshot_height"]
        return snapshot_height

    def get_cycle_total_stake(self, cycle):
        uri = self.api + snapshot_cycle.format(cycle)

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

        resp_json = resp.json()
        staking_supply = resp_json["snapshot_cycle"]["staking_supply"]
        return staking_supply

    def get_current_cycle(self):
        uri = self.api + tip
        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})
        root = resp.json()
        return root["cycle"]

    def fetch_current_balance(self, address_list):
        # sort the address list to have a deterministic uri request
        param_txt = ",".join(sorted(address_list))
        uri = self.api + single_current_balance_call.format(param_txt)

        sleep(0.5)  # be nice to tzpro

        verbose_logger.debug(
            "Requesting current balance of delegator, phase 2, {}".format(uri)
        )

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        verbose_logger.debug(
            "Response from tzpro is {}".format(resp.content.decode("utf8"))
        )

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

        resp = resp.json()

        ret_list = {}
        for item in resp:
            ret_list[item[idx_cb_delegator_address]] = int(
                MUTEZ_PER_TEZ * float(item[idx_cb_current_balance])
            )

        return ret_list

    def get_big_map_id(self, contract_id):
        uri = self.api + contract_storage.format(contract_id)

        verbose_logger.debug("Requesting contract storage, {}".format(uri))

        resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})

        verbose_logger.debug(
            "Response from tzpro is {}".format(resp.content.decode("utf8"))
        )

        if resp.status_code != HTTPStatus.OK:
            # This means something went wrong.
            raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

        resp = resp.json()

        return resp["value"]["accounts"]

    def get_liquidity_providers_list(self, big_map_id, snapshot_block):
        offset = 0
        listLPs = {}
        resp = " "
        while resp != []:
            uri = self.api + balance_LP_call.format(big_map_id, offset, snapshot_block)

            offset += 100
            verbose_logger.debug("Requesting LP balances, {}".format(uri))
            resp = requests.get(uri, timeout=5, headers={"X-API-Key": self.key})
            verbose_logger.debug(
                "Response from tzpro is {}".format(resp.content.decode("utf8"))
            )

            if resp.status_code != HTTPStatus.OK:
                # This means something went wrong.
                raise ApiProviderException("GET {} {}".format(uri, resp.status_code))

            resp = resp.json()
            for item in resp:
                listLPs[item["key"]] = int(item["value"]["balance"])

        return listLPs

    def update_current_balances_dexter(self, balanceMap):
        split_addresses = split(list(balanceMap.keys()), 50)
        for list_address in split_addresses:
            list_curr_balances = self.fetch_current_balance(list_address)
            for d in list_address:
                balanceMap[d].update({"current_balance": list_curr_balances[d]})
