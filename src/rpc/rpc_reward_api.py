from time import sleep

import requests

from api.reward_api import RewardApi
from log_config import main_logger
from model.reward_provider_model import RewardProviderModel

logger = main_logger

COMM_HEAD = "{}/chains/main/blocks/head"
COMM_DELEGATES = "{}/chains/main/blocks/{}/context/delegates/{}"
COMM_BLOCK = "{}/chains/main/blocks/{}"
COMM_SNAPSHOT = COMM_BLOCK + "/context/raw/json/cycle/{}/roll_snapshot"
COMM_DELEGATE_BALANCE = "{}/chains/main/blocks/{}/context/contracts/{}/balance"

class RpcRewardApiImpl(RewardApi):

    def __init__(self, nw, baking_address, node_url, verbose=True):
        super(RpcRewardApiImpl, self).__init__()

        self.name = 'RPC'

        self.blocks_per_cycle = nw['BLOCKS_PER_CYCLE']
        self.preserved_cycles = nw['NB_FREEZE_CYCLE']
        self.blocks_per_roll_snapshot = nw['BLOCKS_PER_ROLL_SNAPSHOT']

        self.baking_address = baking_address
        self.node_url = node_url

        self.verbose = verbose

    def get_rewards_for_cycle_map(self, cycle):
        current_level, current_cycle = self.__get_current_level()
        logger.debug("Current level {}, current cycle {}".format(current_level, current_cycle))

        reward_data = {}
        reward_data["delegate_staking_balance"], reward_data[
            "delegators"] = self.__get_delegators_and_delgators_balances(cycle, current_level)
        reward_data["delegators_nb"] = len(reward_data["delegators"])

        # Get last block in cycle where rewards are unfrozen
        level_of_last_block_in_unfreeze_cycle = (cycle + self.preserved_cycles + 1) * self.blocks_per_cycle

        logger.debug("Cycle {}, preserved cycles {}, blocks per cycle {}, last_block_cycle {}".format(cycle,
                                                                                                      self.preserved_cycles,
                                                                                                      self.blocks_per_cycle,
                                                                                                      level_of_last_block_in_unfreeze_cycle))

        if current_level - level_of_last_block_in_unfreeze_cycle >= 0:
            unfrozen_fees, unfrozen_rewards = self.__get_unfrozen_rewards(level_of_last_block_in_unfreeze_cycle, cycle)
            reward_data["total_rewards"] = unfrozen_fees + unfrozen_rewards

        else:
            logger.warn("Please wait until the rewards and fees for cycle {} are unfrozen".format(cycle))
            reward_data["total_rewards"] = 0

        reward_model = RewardProviderModel(reward_data["delegate_staking_balance"], reward_data["total_rewards"],
                                           reward_data["delegators"])

        logger.debug("delegate_staking_balance = {}, total_rewards = {}".format(reward_data["delegate_staking_balance"],
                                                                              reward_data["total_rewards"]))
        logger.debug("delegators = {}".format(reward_data["delegators"]))

        return reward_model

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
                    if (("level" in balance_update and int(balance_update["level"]) == cycle) or
                        ("cycle" in balance_update and int(balance_update["cycle"]) == cycle)) and int(balance_update["change"]) < 0:
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
                        logger.debug(
                            "[__get_unfrozen_rewards] Found balance update, cycle does not match or change is non-zero, not including: {}".format(
                                balance_update))

        return unfrozen_fees, unfrozen_rewards

    def do_rpc_request(self, request, time_out=120):
        if self.verbose:
            logger.debug("[do_rpc_request] Requesting URL {}".format(request))

        sleep(0.1)  # be nice to public node service

        resp = requests.get(request, timeout=time_out)
        if resp.status_code != 200:
            raise Exception("Request '{} failed with status code {}, after {}, unique request_id {}".format(request, resp.status_code, time_out, resp.headers['CF-RAY']))

        response = resp.json()
        if self.verbose:
            logger.debug("[do_rpc_request] Response {}".format(response))
        return response

    def update_current_balances(self, reward_logs):

        for rl in reward_logs:
            try:
                rl.current_balance = self.__get_current_balance_of_delegator(rl.address)
            except Exception as e:
                logger.warn("update_current_balances - unexpected error: {}".format(e), exc_info=True)
                raise e from e

    def __get_current_level(self):
        head = self.do_rpc_request(COMM_HEAD.format(self.node_url))
        current_level = int(head["metadata"]["level"]["level"])
        current_cycle = int(head["metadata"]["level"]["cycle"])

        return current_level, current_cycle
    
    def __get_delegators_and_delgators_balances(self, cycle, current_level):

        # calculate the hash of the block for the chosen snapshot of the rewards cycle
        roll_snapshot, level_snapshot_block = self.__get_roll_snapshot_block_level(cycle, current_level)
        if level_snapshot_block == "":
            raise RpcRewardApiError("level_snapshot_block is empty. Unable to proceed.")
        if roll_snapshot < 0 or roll_snapshot > 15:
            raise RpcRewardApiError("roll_snapshot is outside allowable range: {} Unable to proceed.".format(roll_snapshot))

        # construct RPC for getting list of delegates and staking balance
        get_delegates_request = COMM_DELEGATES.format(self.node_url, level_snapshot_block, self.baking_address)

        delegate_staking_balance = 0
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

            # loop over delegates; get snapshot balance, and current balance
            delegators_addresses = response["delegated_contracts"]
            d_a_len = len(delegators_addresses)
            
            if d_a_len == 0:
                raise RpcRewardApiError("No delegators found")
            
            # Loop over delegators, get balances
            for idx, delegator in enumerate(delegators_addresses):

                # create new dictionary for each delegator
                d_info = {"staking_balance": 0, "current_balance": 0}

                get_staking_balance_request = COMM_DELEGATE_BALANCE.format(self.node_url, level_snapshot_block, delegator)

                staking_balance_response = None

                while not staking_balance_response:
                    try:
                        staking_balance_response = self.do_rpc_request(get_staking_balance_request, time_out=5)
                    except:
                        logger.debug("Fetching delegator staking balance failed {}, will retry", delegator)

                d_info["staking_balance"] = int(staking_balance_response)

                sleep(0.4) # Be nice to public RPC since we are now making 2x the amount of RPC calls

                d_info["current_balance"] = self.__get_current_balance_of_delegator(delegator)

                logger.debug(
                    "Delegator info ({}/{}) fetched: address {}, staked balance {}, current balance {} ".format(
                        idx+1, d_a_len, delegator, d_info["staking_balance"], d_info["current_balance"]))

                # "append" to master dict
                delegators[delegator] = d_info

            # Sanity check. We should have fetched info for all delegates. If we didn't, something went wrong
            d_len = len(delegators)
            if d_a_len != d_len:
                raise RpcRewardApiError("Did not collect info for all delegators, {}/{}".format(d_a_len, d_len))

        except RpcRewardApiError as r:
            logger.warn("RPC API Error: {}".format(r), exc_info=True)
        except Exception as e:
            logger.warn("Unexpected error: {}".format(e), exc_info=True)

        return delegate_staking_balance, delegators

    def __get_current_balance_of_delegator(self, address):

        """Helper function to get current balance of delegator"""

        get_current_balance_request = COMM_DELEGATE_BALANCE.format(self.node_url, "head", address)

        current_balance_response = None

        while not current_balance_response:
            sleep(0.4) # Be nice to public RPC
            try:
                current_balance_response = self.do_rpc_request(get_current_balance_request, time_out=5)
            except requests.exceptions.RequestException as e:
                # Catch HTTP-related errors and retry
                logger.debug("Fetching delegator {} current balance failed, will retry: {}", address, e)
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

            level_snapshot_block = (cycle - self.preserved_cycles - 2) * self.blocks_per_cycle + (
                    chosen_snapshot + 1) * self.blocks_per_roll_snapshot

            logger.debug("Snapshot index {}, snapshot index level {}".format(chosen_snapshot, level_snapshot_block))

            return chosen_snapshot, level_snapshot_block

        else:
            logger.info("Cycle too far in the future")
            return 0, ""

class RpcRewardApiError(Exception):
    pass
