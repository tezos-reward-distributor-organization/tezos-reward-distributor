from time import sleep

import requests
from http import HTTPStatus

from api.reward_api import RewardApi
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger
from model.reward_provider_model import RewardProviderModel
from Dexter import dexter_utils as dxtz
from Constants import MAX_SEQUENT_CALLS

logger = main_logger.getChild("rpc_reward_api")

# RPC constants
COMM_HEAD = "{}/chains/main/blocks/head"
COMM_DELEGATES = "{}/chains/main/blocks/{}/context/delegates/{}"
COMM_BLOCK = "{}/chains/main/blocks/{}"
COMM_BLOCK_METADATA = "{}/chains/main/blocks/{}/metadata"
COMM_BLOCK_OPERATIONS = "{}/chains/main/blocks/{}/operations"
COMM_SNAPSHOT = COMM_BLOCK + "/context/raw/json/cycle/{}/roll_snapshot"
COMM_DELEGATE_BALANCE = "{}/chains/main/blocks/{}/context/contracts/{}/balance"
COMM_CONTRACT_STORAGE = "{}/chains/main/blocks/{}/context/contracts/{}/storage"
COMM_BIGMAP_QUERY = "{}/chains/main/blocks/{}/context/big_maps/{}/{}"
COMM_BAKING_RIGHTS = (
    "{}/chains/main/blocks/{}/helpers/baking_rights?cycle={}&delegate={}"
)
COMM_ENDORSING_RIGHTS = (
    "{}/chains/main/blocks/{}/helpers/endorsing_rights?cycle={}&delegate={}"
)
COMM_FROZEN_BALANCE = (
    "{}/chains/main/blocks/{}/context/delegates/{}/frozen_balance_by_cycle"
)

# Constants used for calculations related to the cycles before Granada
CYCLES_BEFORE_GRANADA = 388
BLOCKS_BEFORE_GRANADA = 1589248
BLOCKS_PER_CYCLE_BEFORE_GRANADA = 4096
BLOCK_PER_ROLL_SNAPSHOT_BEFORE_GRANADA = 256
FIRST_CYCLE_REWARDS_GRANADA = 394
FIRST_CYCLE_SNAPSHOT_GRANADA = 396

RPC_REQUEST_BUFFER_SECONDS = 0.4
RPC_RETRY_TIMEOUT_SECONDS = 2.0


class RpcRewardApiImpl(RewardApi):
    def __init__(self, nw, baking_address, node_url):
        super(RpcRewardApiImpl, self).__init__()

        self.name = "RPC"

        self.blocks_per_cycle = nw["BLOCKS_PER_CYCLE"]
        self.preserved_cycles = nw["NB_FREEZE_CYCLE"]
        self.blocks_per_roll_snapshot = nw["BLOCKS_PER_ROLL_SNAPSHOT"]
        self.block_reward = nw["BLOCK_REWARD"]
        self.endorsement_reward = nw["ENDORSEMENT_REWARD"]

        self.baking_address = baking_address
        self.node_url = node_url

    def get_rewards_for_cycle_map(self, cycle, rewards_type):
        try:
            current_level, current_cycle = self.__get_current_level()
            logger.debug(
                "Current level {:d}, current cycle {:d}".format(
                    current_level, current_cycle
                )
            )

            reward_data = {}
            (
                reward_data["delegate_staking_balance"],
                reward_data["delegators"],
            ) = self.__get_delegators_and_delgators_balances(cycle, current_level)
            reward_data["delegators_nb"] = len(reward_data["delegators"])

            # Get last block in cycle where rewards are unfrozen
            if cycle >= FIRST_CYCLE_REWARDS_GRANADA:
                # Since cycle 394, we use an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
                # Cycles start at 0
                level_of_last_block_in_unfreeze_cycle = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA + self.preserved_cycles + 1)
                    * self.blocks_per_cycle
                )
                level_of_first_block_in_preserved_cycles = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles)
                    * self.blocks_per_cycle
                    + 1
                )
            else:
                # Using pre-Granada calculation
                level_of_last_block_in_unfreeze_cycle = (
                    cycle + self.preserved_cycles + 1
                ) * BLOCKS_PER_CYCLE_BEFORE_GRANADA
                level_of_first_block_in_preserved_cycles = (
                    cycle - self.preserved_cycles
                ) * BLOCKS_PER_CYCLE_BEFORE_GRANADA + 1

            logger.debug(
                "Cycle {:d}, preserved cycles {:d}, blocks per cycle {:d}, last block of cycle {:d}, "
                "last block unfreeze cycle {:d}".format(
                    cycle,
                    self.preserved_cycles,
                    self.blocks_per_cycle,
                    level_of_first_block_in_preserved_cycles,
                    level_of_last_block_in_unfreeze_cycle,
                )
            )

            # Determine how many priority 0 baking rights delegate had
            baking_rights = self.__get_baking_rights(
                cycle, level_of_first_block_in_preserved_cycles
            )
            endorsement_rights = self.__get_endorsement_rights(
                cycle, level_of_first_block_in_preserved_cycles
            )
            nb_blocks = len([r for r in baking_rights if r["priority"] == 0])
            nb_endorsements = sum([len(r["slots"]) for r in endorsement_rights])

            total_reward_amount = None
            if not rewards_type.isEstimated():
                # Calculate actual rewards
                if current_level - level_of_last_block_in_unfreeze_cycle >= 0:
                    unfrozen_fees, unfrozen_rewards = self.__get_unfrozen_rewards(
                        level_of_last_block_in_unfreeze_cycle, cycle
                    )
                    total_reward_amount = unfrozen_fees + unfrozen_rewards
                else:
                    frozen_fees, frozen_rewards = self.__get_frozen_rewards(
                        cycle, current_level
                    )
                    total_reward_amount = frozen_fees + frozen_rewards

            # Without an indexer, it is not possible to itemize rewards
            # so setting these values below to "None"
            rewards_and_fees = None
            equivocation_losses = None
            denunciation_rewards = None

            offline_losses = None
            if rewards_type.isIdeal():
                # Calculate offline losses
                missed_baking_income = 0
                for count, r in enumerate(baking_rights):
                    if count % 10 == 0:
                        logger.info(
                            "Verifying bake ({}/{}).".format(count, len(baking_rights))
                        )
                    if r["priority"] == 0:
                        if self.__get_block_author(r["level"]) != self.baking_address:
                            logger.warning(
                                "Found missed baking slot {}, adding {} mutez reward anyway.".format(
                                    r, self.block_reward
                                )
                            )
                            missed_baking_income += self.block_reward
                missed_endorsing_income = 0
                for count, r in enumerate(endorsement_rights):
                    if count % 10 == 0:
                        logger.info(
                            "Verifying endorsement ({}/{}).".format(
                                count, len(endorsement_rights)
                            )
                        )
                    authored_endorsement_slots = (
                        self.__get_authored_endorsement_slots_by_level(r["level"] + 1)
                    )
                    if authored_endorsement_slots != r["slots"]:
                        mutez_to_add = self.endorsement_reward * len(r["slots"])
                        logger.warning(
                            "Found {} missed endorsement(s) at level {}, adding {} mutez reward anyway.".format(
                                len(r["slots"]), r["level"], mutez_to_add
                            )
                        )
                        missed_endorsing_income += mutez_to_add
                offline_losses = missed_baking_income + missed_endorsing_income

            # TODO: support Dexter for RPC
            # _, snapshot_level = self.__get_roll_snapshot_block_level(cycle, current_level)
            # for delegator in self.dexter_contracts_set:
            #     dxtz.process_original_delegators_map(reward_data["delegators"], delegator, snapshot_level)

            reward_model = RewardProviderModel(
                reward_data["delegate_staking_balance"],
                nb_blocks,
                nb_endorsements,
                total_reward_amount,
                rewards_and_fees,
                equivocation_losses,
                denunciation_rewards,
                offline_losses,
                reward_data["delegators"],
                None,
            )

            logger.debug(
                "delegate_staking_balance = {:d}".format(
                    reward_data["delegate_staking_balance"]
                )
            )
            logger.debug("delegators = {}".format(reward_data["delegators"]))

            return reward_model

        except Exception as e:
            # We should abort here on any exception as we did not fetch all
            # necessary data to properly compute rewards
            raise e from e

    def __get_response(self, address, request_function, response=None):
        retry_count = 0
        while (not response) and (retry_count < MAX_SEQUENT_CALLS):
            retry_count += 1
            sleep(RPC_REQUEST_BUFFER_SECONDS)  # Be nice to public RPC
            try:
                logger.info("Fetching address {:s} ...".format(address))
                response = self.do_rpc_request(
                    request_function, time_out=5
                )
            except requests.exceptions.RequestException as e:
                # Catch HTTP-related errors and retry
                logger.warning(
                    "Failed with exception, will retry ({}) : {}".format(
                        retry_count, str(e)
                    )
                )
                sleep(RPC_RETRY_TIMEOUT_SECONDS)
            except Exception as e:
                # Anything else, raise up
                raise e from e

        return response

    def __get_baking_rights(self, cycle, level):
        """
        Returns list of baking rights for a given cycle.
        """

        try:
            baking_rights_rpc = COMM_BAKING_RIGHTS.format(
                self.node_url, level, cycle, self.baking_address
            )
            return self.do_rpc_request(baking_rights_rpc)

        except ApiProviderException as e:
            raise e from e

    def __get_block_author(self, level):
        """
        Returns baker public key hash for a given block level.
        """

        try:
            block_metadata_rpc = COMM_BLOCK_METADATA.format(self.node_url, level)
            return self.do_rpc_request(block_metadata_rpc)["baker"]

        except ApiProviderException as e:
            raise e from e

    def __get_endorsement_rights(self, cycle, level):
        """
        Returns list of endorsements rights for a cycle.
        """

        try:
            endorsing_rights_rpc = COMM_ENDORSING_RIGHTS.format(
                self.node_url, level, cycle, self.baking_address
            )
            return self.do_rpc_request(endorsing_rights_rpc)

        except ApiProviderException as e:
            raise e from e

    def __get_authored_endorsement_slots_by_level(self, level):
        """
        Returns a list of endorsements authored by the baker for a given block level.
        """

        try:
            block_operations_rpc = COMM_BLOCK_OPERATIONS.format(self.node_url, level)
            block_operations = self.do_rpc_request(block_operations_rpc)[0]
            endorsements = [
                b
                for b in block_operations
                if b["contents"][0]["kind"] == "endorsement_with_slot"
            ]
            if len(endorsements) == 0:
                logger.error("Can not parse endorsements from RPC. Aborting.")
                logger.info(
                    "TRD can not process rewards for protocols older than Florence."
                )
                raise Exception("Can not parse endorsements from RPC.")

            for e in endorsements:
                if e["contents"][0]["metadata"]["delegate"] == self.baking_address:
                    return e["contents"][0]["metadata"]["slots"]
            return []

        except ApiProviderException as e:
            raise e from e

    def __get_frozen_rewards(self, cycle, current_level):
        try:
            frozen_balance_by_cycle_rpc = COMM_FROZEN_BALANCE.format(
                self.node_url, current_level, self.baking_address
            )
            f = [
                f
                for f in self.do_rpc_request(frozen_balance_by_cycle_rpc)
                if f["cycle"] == cycle
            ][0]

            return int(f["fees"]), int(f["rewards"])

        except ApiProviderException as e:
            raise e from e

    def __get_unfrozen_rewards(self, level_of_last_block_in_unfreeze_cycle, cycle):
        request_metadata = (
            COMM_BLOCK.format(self.node_url, level_of_last_block_in_unfreeze_cycle)
            + "/metadata"
        )
        metadata = self.do_rpc_request(request_metadata)
        balance_updates = metadata["balance_updates"]
        unfrozen_rewards = unfrozen_fees = 0

        for i in range(len(balance_updates)):
            balance_update = balance_updates[i]
            if balance_update["kind"] == "freezer":
                if balance_update["delegate"] == self.baking_address:
                    # Protocols < Athens (004) mistakenly used 'level'
                    if (
                        (
                            "level" in balance_update
                            and int(balance_update["level"]) == cycle
                        )
                        or (
                            "cycle" in balance_update
                            and int(balance_update["cycle"]) == cycle
                        )
                    ) and int(balance_update["change"]) < 0:

                        if balance_update["category"] == "rewards":
                            unfrozen_rewards = -int(balance_update["change"])
                            logger.debug(
                                "[__get_unfrozen_rewards] Found balance update for reward {}".format(
                                    balance_update
                                )
                            )
                        elif balance_update["category"] == "fees":
                            unfrozen_fees = -int(balance_update["change"])
                            logger.debug(
                                "[__get_unfrozen_rewards] Found balance update for fee {}".format(
                                    balance_update
                                )
                            )
                        else:
                            logger.debug(
                                "[__get_unfrozen_rewards] Found balance update, not including: {}".format(
                                    balance_update
                                )
                            )
                    else:
                        logger.debug(
                            "[__get_unfrozen_rewards] Found balance update, cycle does not match or "
                            "change is non-zero, not including: {}".format(
                                balance_update
                            )
                        )

        return unfrozen_fees, unfrozen_rewards

    def do_rpc_request(self, request, time_out=120):

        verbose_logger.debug("[do_rpc_request] Requesting URL {:s}".format(request))

        sleep(0.1)  # be nice to public node service

        try:
            resp = requests.get(request, timeout=time_out)
        except requests.exceptions.Timeout:
            # Catches both ConnectTimeout and ReadTimeout
            message = (
                "[do_rpc_request] Requesting URL '{:s}' timed out after {:d}s".format(
                    request, time_out
                )
            )
            logger.error(message)
            raise ApiProviderException(message)
        except requests.exceptions.RequestException as e:
            # Catches all other requests exceptions
            message = (
                "[do_rpc_request] Requesting URL '{:s}' Generic Error: {:s}".format(
                    request, str(e)
                )
            )
            logger.error(message)
            raise ApiProviderException(message)

        # URL not found
        if resp.status_code == HTTPStatus.NOT_FOUND:
            raise ApiProviderException(
                "RPC URL '{}' not found. Is this node in archive mode?".format(request)
            )

        # URL returned something broken from the client side 4xx
        # server side errors 5xx can pass for a retry
        if (
            HTTPStatus.BAD_REQUEST
            <= resp.status_code
            < HTTPStatus.INTERNAL_SERVER_ERROR
        ):
            message = "[do_rpc_request] Requesting URL '{:s}' failed ({:d})".format(
                request, resp.status_code
            )
            if "CF-RAY" in resp.headers:

                message += ", unique request_id: {:s}".format(resp.headers["CF-RAY"])
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
                logger.warning(
                    "update_current_balances - unexpected error: {}".format(str(e)),
                    exc_info=True,
                )
                raise e from e

    def get_contract_storage(self, contract_id, block):
        get_contract_storage_request = COMM_CONTRACT_STORAGE.format(
            self.node_url, block, contract_id
        )
        return self.__get_response(contract_id, get_contract_storage_request)

    def get_big_map_id(self, contract_id):
        storage = self.get_contract_storage(contract_id, "head")
        parsed_storage = dxtz.parse_dexter_storage(storage)
        return parsed_storage["big_map_id"]

    def get_address_value_from_big_map(
        self, big_map_id, address_script_expr, snapshot_block
    ):
        get_address_value_request = COMM_BIGMAP_QUERY.format(
            self.node_url, snapshot_block, big_map_id, address_script_expr
        )
        return self.__get_response(address_script_expr, get_address_value_request)

    def get_liquidity_provider_balance(
        self, big_map_id, address_script_expr, snapshot_block
    ):
        big_map_value = self.get_address_value_from_big_map(
            big_map_id, address_script_expr, snapshot_block
        )
        int(big_map_value.json()["args"][0]["int"])

    def get_liquidity_providers_list(self, big_map_id, snapshot_block):
        pass

    def update_current_balances_dexter(self, balanceMap):
        for address in balanceMap:
            curr_balance = self.__get_current_balance_of_delegator(address)
            balanceMap[address].update({"current_balance": curr_balance})

    def __get_current_level(self):
        head = self.do_rpc_request(COMM_HEAD.format(self.node_url))
        current_level = int(head["metadata"]["level_info"]["level"])
        current_cycle = int(head["metadata"]["level_info"]["cycle"])

        return current_level, current_cycle

    def __get_delegators_and_delgators_balances(self, cycle, current_level):

        # calculate the hash of the block for the chosen snapshot of the rewards cycle
        roll_snapshot, level_snapshot_block = self.__get_roll_snapshot_block_level(
            cycle, current_level
        )
        if level_snapshot_block == "":
            raise ApiProviderException(
                "[get_d_d_b] level_snapshot_block is empty. Unable to proceed."
            )
        if roll_snapshot < 0 or roll_snapshot > 15:
            raise ApiProviderException(
                "[get_d_d_b] roll_snapshot is outside allowable range: {} Unable to proceed.".format(
                    roll_snapshot
                )
            )

        # construct RPC for getting list of delegates and staking balance
        get_delegates_request = COMM_DELEGATES.format(
            self.node_url, level_snapshot_block, self.baking_address
        )

        delegate_staking_balance = 0
        d_a_len = 0
        delegators = {}

        try:
            # get RPC response for delegates and staking balance
            response = self.do_rpc_request(get_delegates_request)
            delegate_staking_balance = int(response["staking_balance"])

            # If roll_snapshot == 15, we need to adjust the baker's staking balance
            # by subtracting unfrozen rewards due to when the snapshot is taken
            # within the block context. For more information, see:
            # https://medium.com/@_MisterWalker_/we-all-were-wrong-baking-bad-and-most-bakers-were-using-wrong-data-to-calculate-staking-rewards-a8c26f5ec62b
            if roll_snapshot == 15:
                if cycle >= FIRST_CYCLE_REWARDS_GRANADA:
                    # Since cycle 394, we use an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
                    # Cycles start at 0.
                    old_rewards_cycle = (
                        CYCLES_BEFORE_GRANADA
                        + (
                            (level_snapshot_block - BLOCKS_BEFORE_GRANADA)
                            / self.blocks_per_cycle
                        )
                        - self.preserved_cycles
                        - 1
                    )
                else:
                    old_rewards_cycle = (
                        (level_snapshot_block / BLOCKS_PER_CYCLE_BEFORE_GRANADA)
                        - self.preserved_cycles
                        - 1
                    )
                _, unfrozen_rewards = self.__get_unfrozen_rewards(
                    level_snapshot_block, old_rewards_cycle
                )
                delegate_staking_balance -= unfrozen_rewards

            # Remove baker's address from list of delegators
            delegators_addresses = list(
                filter(
                    lambda x: x != self.baking_address, response["delegated_contracts"]
                )
            )
            d_a_len = len(delegators_addresses)

            if d_a_len == 0:
                raise ApiProviderException("[get_d_d_b] No delegators found")

            # Loop over delegators; get snapshot balance, and current balance
            for idx, delegator in enumerate(delegators_addresses):
                # create new dictionary for each delegator
                d_info = {"staking_balance": 0, "current_balance": 0}

                get_staking_balance_request = COMM_DELEGATE_BALANCE.format(
                    self.node_url, level_snapshot_block, delegator
                )
                d_info["staking_balance"] = int(self.__get_response(delegator, get_staking_balance_request))

                sleep(
                    0.5
                )  # Be nice to public RPC since we are now making 2x the amount of RPC calls

                d_info["current_balance"] = self.__get_current_balance_of_delegator(
                    delegator
                )

                logger.debug(
                    "Delegator info ({}/{}) fetched: address {}, staked balance {}, current balance {} ".format(
                        idx + 1,
                        d_a_len,
                        delegator,
                        d_info["staking_balance"],
                        d_info["current_balance"],
                    )
                )
                if idx % 10 == 0:
                    logger.info(
                        "Delegator info ({}/{}) fetched.".format(idx + 1, d_a_len)
                    )

                # "append" to master dict
                delegators[delegator] = d_info

        except ApiProviderException as r:
            logger.error("[get_d_d_b] RPC API Error: {}".format(str(r)))
            raise r from r
        except Exception as e:
            logger.error(
                "[get_d_d_b] Unexpected error: {}".format(str(e)), exc_info=True
            )
            raise e from e

        # Sanity check. We should have fetched info for all delegates. If we didn't, something went wrong
        d_len = len(delegators)
        if d_a_len != d_len:
            raise ApiProviderException(
                "[get_d_d_b] Did not collect info for all delegators, {}/{}".format(
                    d_a_len, d_len
                )
            )

        return delegate_staking_balance, delegators

    def __get_current_balance_of_delegator(self, address):

        """Helper function to get current balance of delegator"""

        get_current_balance_request = COMM_DELEGATE_BALANCE.format(
            self.node_url, "head", address
        )
        return int(self.__get_response(address, get_current_balance_request))

    def __get_roll_snapshot_block_level(self, cycle, current_level):
        # Granada doubled the number of [blocks_per_cycle] (8192 vs 4096)
        # Thus, we need to change the way we calculate the snapshot level
        # If the cycle is one of the 6 next after Granada (388-393),
        # the calculation is the same. After cycle 393, we have to consider that
        # the initial cycle has to be calculated differently, adding an offset.
        # For example, for cycle 394:
        # e.g. snapshot_level = 1589248 + ((394 - 388 - 5) * 8192 + 1)

        if cycle >= FIRST_CYCLE_REWARDS_GRANADA:
            # Since cycle 394, we use an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
            # Cycles start at 0
            snapshot_level = BLOCKS_BEFORE_GRANADA + (
                (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles)
                * self.blocks_per_cycle
                + 1
            )
        else:
            # Using pre-Granada calculation
            snapshot_level = (
                cycle - self.preserved_cycles
            ) * BLOCKS_PER_CYCLE_BEFORE_GRANADA + 1

        logger.debug("Reward cycle {}, snapshot level {}".format(cycle, snapshot_level))

        if current_level - snapshot_level >= 0:
            request = COMM_SNAPSHOT.format(self.node_url, snapshot_level, cycle)
            chosen_snapshot = self.do_rpc_request(request)

            if cycle >= FIRST_CYCLE_SNAPSHOT_GRANADA:
                # Using an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
                level_snapshot_block = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles - 2)
                    * self.blocks_per_cycle
                    + (chosen_snapshot + 1) * self.blocks_per_roll_snapshot
                )
            else:
                # Using pre-Granada calculation
                level_snapshot_block = (
                    cycle - self.preserved_cycles - 2
                ) * BLOCKS_PER_CYCLE_BEFORE_GRANADA + (
                    chosen_snapshot + 1
                ) * BLOCK_PER_ROLL_SNAPSHOT_BEFORE_GRANADA

            logger.debug(
                "Snapshot index {}, snapshot index level {}".format(
                    chosen_snapshot, level_snapshot_block
                )
            )

            return chosen_snapshot, level_snapshot_block

        else:
            logger.info("Cycle too far in the future")
            return 0, ""
