from time import sleep

import requests

from api.reward_api import RewardApi
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger
from model.reward_provider_model import RewardProviderModel
from Dexter import dexter_utils as dxtz

logger = main_logger

COMM_HEAD = "{}/chains/main/blocks/head"
COMM_DELEGATES = "{}/chains/main/blocks/{}/context/delegates/{}"
COMM_BLOCK = "{}/chains/main/blocks/{}"
COMM_SNAPSHOT = COMM_BLOCK + "/context/raw/json/cycle/{}/roll_snapshot"
COMM_DELEGATE_BALANCE = "{}/chains/main/blocks/{}/context/contracts/{}/balance"
COMM_CONTRACT_STORAGE = "{}/chains/main/blocks/{}/context/contracts/{}/storage"
COMM_BIGMAP_QUERY = "{}/chains/main/blocks/{}/context/big_maps/{}/{}"


class RpcRewardApiImpl(RewardApi):

    def __init__(self, nw, baking_address, node_url):
        super(RpcRewardApiImpl, self).__init__()

        self.name = 'RPC'

        self.blocks_per_cycle = nw['BLOCKS_PER_CYCLE']
        self.preserved_cycles = nw['NB_FREEZE_CYCLE']
        self.blocks_per_roll_snapshot = nw['BLOCKS_PER_ROLL_SNAPSHOT']

        self.baking_address = baking_address
        self.node_url = node_url

    def get_rewards_for_cycle_map(self, cycle):
        try:
            current_level, current_cycle = self.__get_current_level()
            logger.debug("Current level {:d}, current cycle {:d}".format(current_level, current_cycle))

            reward_data = {}
            reward_data["delegate_staking_balance"], reward_data[
                "delegators"] = self.__get_delegators_and_delgators_balances(cycle, current_level)
            reward_data["delegators_nb"] = len(reward_data["delegators"])

            # Get last block in cycle where rewards are unfrozen
            level_of_last_block_in_unfreeze_cycle = (cycle + self.preserved_cycles + 1) * self.blocks_per_cycle

            logger.debug("Cycle {:d}, preserved cycles {:d}, blocks per cycle {:d}, last block of cycle {:d}"
                         .format(cycle, self.preserved_cycles, self.blocks_per_cycle,
                                 level_of_last_block_in_unfreeze_cycle))

            if current_level - level_of_last_block_in_unfreeze_cycle >= 0:
                unfrozen_fees, unfrozen_rewards = self.__get_unfrozen_rewards(level_of_last_block_in_unfreeze_cycle, cycle)
                reward_data["total_rewards"] = unfrozen_fees + unfrozen_rewards
            else:
                logger.warning("Please wait until the rewards and fees for cycle {:d} are unfrozen".format(cycle))
                reward_data["total_rewards"] = 0

            _, snapshot_level = self.__get_roll_snapshot_block_level(cycle, current_level)
            for delegator in self.dexter_contracts_set:
                dxtz.process_original_delegators_map(reward_data["delegators"], delegator, snapshot_level)

            reward_model = RewardProviderModel(reward_data["delegate_staking_balance"], reward_data["total_rewards"],
                                               reward_data["delegators"])

            logger.debug("delegate_staking_balance = {:d}, total_rewards = {:d}"
                         .format(reward_data["delegate_staking_balance"], reward_data["total_rewards"]))
            logger.debug("delegators = {}".format(reward_data["delegators"]))

            return reward_model

        except Exception as e:
            # We should abort here on any exception as we did not fetch all
            # necessary data to properly compute rewards
            raise e from e

    def __get_unfrozen_rewards(self, level_of_last_block_in_unfreeze_cycle, cycle):
        request_metadata = COMM_BLOCK.format(self.node_url, level_of_last_block_in_unfreeze_cycle) + '/metadata'
        metadata = self.do_rpc_request(request_metadata)
        balance_updates = metadata["balance_updates"]
        unfrozen_rewards = unfrozen_fees = 0

        for i in range(len(balance_updates)):
            balance_update = balance_updates[i]
            if balance_update["kind"] == "freezer":
                if balance_update["delegate"] == self.baking_address:
                    # Protocols < Athens (004) mistakenly used 'level'
                    if (("level" in balance_update and int(balance_update["level"]) == cycle)
                        or ("cycle" in balance_update and int(balance_update["cycle"]) == cycle)) \
                            and int(balance_update["change"]) < 0:

                        if balance_update["category"] == "rewards":
                            unfrozen_rewards = -int(balance_update["change"])
                            logger.debug(
                                "[__get_unfrozen_rewards] Found balance update for reward {}".format(balance_update))
                        elif balance_update["category"] == "fees":
                            unfrozen_fees = -int(balance_update["change"])
                            logger.debug(
                                "[__get_unfrozen_rewards] Found balance update for fee {}".format(balance_update))
                        else:
                            logger.debug("[__get_unfrozen_rewards] Found balance update, not including: {}".format(
                                balance_update))
                    else:
                        logger.debug("[__get_unfrozen_rewards] Found balance update, cycle does not match or "
                                     "change is non-zero, not including: {}".format(balance_update))

        return unfrozen_fees, unfrozen_rewards

    def do_rpc_request(self, request, time_out=120):

        verbose_logger.debug("[do_rpc_request] Requesting URL {:s}".format(request))

        sleep(0.1)  # be nice to public node service

        try:
            resp = requests.get(request, timeout=time_out)
        except requests.exceptions.Timeout:
            # Catches both ConnectTimeout and ReadTimeout
            message = "[do_rpc_request] Requesting URL '{:s}' timed out after {:d}s".format(request, time_out)
            logger.error(message)
            raise ApiProviderException(message)
        except requests.exceptions.RequestException as e:
            # Catches all other requests exceptions
            message = "[do_rpc_request] Requesting URL '{:s}' Generic Error: {:s}".format(request, str(e))
            logger.error(message)
            raise ApiProviderException(message)

        # URL not found
        if resp.status_code == 404:
            raise ApiProviderException("RPC URL '{}' not found. Is this node in archive mode?".format(request))

        # URL returned something broken
        if resp.status_code != 200:
            message = "[do_rpc_request] Requesting URL '{:s}' failed ({:d})".format(request, resp.status_code)
            if "CF-RAY" in resp.headers:

                message += ", unique request_id: {:s}".format(resp.headers['CF-RAY'])
            raise ApiProviderException(message)

        # URL fetch succeeded; parse to JSON object
        response = resp.json()

        verbose_logger.debug("[do_rpc_request] Response {:s}".format(str(response)))

        return response

    def update_current_balances(self, reward_logs):

        for rl in reward_logs:
            try:
                rl.current_balance = self.__get_current_balance_of_delegator(rl.address)
            except Exception as e:
                logger.warning("update_current_balances - unexpected error: {}".format(str(e)), exc_info=True)
                raise e from e

    def get_contract_storage(self, contract_id, block):
        get_contract_storage_request = COMM_CONTRACT_STORAGE.format(self.node_url, block, contract_id)

        contract_storage_response = None

        while not contract_storage_response:
            sleep(0.4)  # Be nice to public RPC
            try:
                contract_storage_response = self.do_rpc_request(get_contract_storage_request, time_out=5)
            except requests.exceptions.RequestException as e:
                # Catch HTTP-related errors and retry
                logger.debug("Fetching contract storage {:s} failed, will retry: {:s}".format(contract_id, str(e)))
                sleep(2.0)
            except Exception as e:
                # Anything else, raise up
                raise e from e

        return contract_storage_response

    def get_big_map_id(self, contract_id):
        storage = self.get_contract_storage(contract_id, 'head')
        parsed_storage = dxtz.parse_dexter_storage(storage)
        return parsed_storage['big_map_id']

    def get_address_value_from_big_map(self, big_map_id, address_script_expr, snapshot_block):
        get_address_value_request = COMM_BIGMAP_QUERY.format(self.node_url, snapshot_block, big_map_id,
                                                             address_script_expr)

        address_value_response = None

        while not address_value_response:
            sleep(0.4)  # Be nice to public RPC
            try:
                address_value_response = self.do_rpc_request(get_address_value_request, time_out=5)
            except requests.exceptions.RequestException as e:
                # Catch HTTP-related errors and retry
                logger.debug("Fetching address value {} failed, will retry: {:s}".format(address_script_expr, str(e)))
                sleep(2.0)
            except Exception as e:
                # Anything else, raise up
                raise e from e

        return address_value_response

    def get_liquidity_provider_balance(self, big_map_id, address_script_expr, snapshot_block):
        big_map_value = self.get_address_value_from_big_map(big_map_id, address_script_expr, snapshot_block)
        int(big_map_value.json()['args'][0]['int'])

    def get_liquidity_providers_list(self, big_map_id, snapshot_block):
        pass

    def update_current_balances_dexter(self, balanceMap):
        for address in balanceMap:
            curr_balance = self.__get_current_balance_of_delegator(address)
            balanceMap[address].update({"current_balance": curr_balance})

    def __get_current_level(self):
        head = self.do_rpc_request(COMM_HEAD.format(self.node_url))
        current_level = int(head["metadata"]["level"]["level"])
        current_cycle = int(head["metadata"]["level"]["cycle"])

        return current_level, current_cycle

    def __get_delegators_and_delgators_balances(self, cycle, current_level):

        # calculate the hash of the block for the chosen snapshot of the rewards cycle
        roll_snapshot, level_snapshot_block = self.__get_roll_snapshot_block_level(cycle, current_level)
        if level_snapshot_block == "":
            raise ApiProviderException("[get_d_d_b] level_snapshot_block is empty. Unable to proceed.")
        if roll_snapshot < 0 or roll_snapshot > 15:
            raise ApiProviderException("[get_d_d_b] roll_snapshot is outside allowable range: {} Unable to proceed.".format(roll_snapshot))

        # construct RPC for getting list of delegates and staking balance
        get_delegates_request = COMM_DELEGATES.format(self.node_url, level_snapshot_block, self.baking_address)

        delegate_staking_balance = 0
        d_a_len = 0
        delegators = {}

        try:
            # get RPC response for delegates and staking balance
            response = self.do_rpc_request(get_delegates_request)
            delegate_staking_balance = int(response["staking_balance"])

            # If roll_snapshot == 15, we need to adjust the baker's staking balance
            # by subtracting unfrozen rewards due to when the snapshot is taken
            # within the block context
            if roll_snapshot == 15:
                old_rewards_cycle = (level_snapshot_block / self.blocks_per_cycle) - self.preserved_cycles - 1
                _, unfrozen_rewards = self.__get_unfrozen_rewards(level_snapshot_block, old_rewards_cycle)
                delegate_staking_balance -= unfrozen_rewards

            # Remove baker's address from list of delegators
            delegators_addresses = list(filter(lambda x: x != self.baking_address, response["delegated_contracts"]))
            d_a_len = len(delegators_addresses)

            if d_a_len == 0:
                raise ApiProviderException("[get_d_d_b] No delegators found")

            # Loop over delegators; get snapshot balance, and current balance
            for idx, delegator in enumerate(delegators_addresses):
                # create new dictionary for each delegator
                d_info = {"staking_balance": 0, "current_balance": 0}

                get_staking_balance_request = COMM_DELEGATE_BALANCE.format(self.node_url, level_snapshot_block,
                                                                           delegator)

                staking_balance_response = None

                while not staking_balance_response:
                    try:
                        staking_balance_response = self.do_rpc_request(get_staking_balance_request, time_out=5)
                    except Exception as e:
                        logger.debug("[get_d_d_b] Fetching delegator {:s} staking balance failed: {:s}, will retry".format(delegator, str(e)))
                        sleep(1.0)  # Sleep between failure

                d_info["staking_balance"] = int(staking_balance_response)

                sleep(0.5)  # Be nice to public RPC since we are now making 2x the amount of RPC calls

                d_info["current_balance"] = self.__get_current_balance_of_delegator(delegator)

                logger.debug(
                    "Delegator info ({}/{}) fetched: address {}, staked balance {}, current balance {} ".format(
                        idx + 1, d_a_len, delegator, d_info["staking_balance"], d_info["current_balance"]))

                # "append" to master dict
                delegators[delegator] = d_info

        except ApiProviderException as r:
            logger.error("[get_d_d_b] RPC API Error: {}".format(str(r)))
            raise r from r
        except Exception as e:
            logger.error("[get_d_d_b] Unexpected error: {}".format(str(e)), exc_info=True)
            raise e from e

        # Sanity check. We should have fetched info for all delegates. If we didn't, something went wrong
        d_len = len(delegators)
        if d_a_len != d_len:
            raise ApiProviderException("[get_d_d_b] Did not collect info for all delegators, {}/{}".format(d_a_len, d_len))

        return delegate_staking_balance, delegators

    def __get_current_balance_of_delegator(self, address):

        """Helper function to get current balance of delegator"""

        get_current_balance_request = COMM_DELEGATE_BALANCE.format(self.node_url, "head", address)

        current_balance_response = None

        while not current_balance_response:
            sleep(0.4)  # Be nice to public RPC
            try:
                current_balance_response = self.do_rpc_request(get_current_balance_request, time_out=5)
            except ApiProviderException as e:
                # Catch HTTP-related errors and retry
                logger.warning(
                    "Fetching delegator {:s} current balance failed, will retry: {:s}".format(address, str(e)))
                sleep(2.0)
            except Exception as e:
                # Anything else, raise up
                raise e from e

        return int(current_balance_response)

    def __get_roll_snapshot_block_level(self, cycle, current_level):

        snapshot_level = (cycle - self.preserved_cycles) * self.blocks_per_cycle + 1
        logger.debug("Reward cycle {}, snapshot level {}".format(cycle, snapshot_level))

        block_level = cycle * self.blocks_per_cycle + 1

        if current_level - snapshot_level >= 0:
            request = COMM_SNAPSHOT.format(self.node_url, block_level, cycle)
            chosen_snapshot = self.do_rpc_request(request)

            level_snapshot_block = ((cycle - self.preserved_cycles - 2) * self.blocks_per_cycle
                                    + (chosen_snapshot + 1) * self.blocks_per_roll_snapshot)

            logger.debug("Snapshot index {}, snapshot index level {}".format(chosen_snapshot, level_snapshot_block))

            return chosen_snapshot, level_snapshot_block

        else:
            logger.info("Cycle too far in the future")
            return 0, ""
