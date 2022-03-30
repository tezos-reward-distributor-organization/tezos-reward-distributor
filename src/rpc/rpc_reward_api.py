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
COMM_MANAGER_KEY = "{}/chains/main/blocks/{}/context/contracts/{}/manager_key"
COMM_BLOCK = "{}/chains/main/blocks/{}"
COMM_BLOCK_METADATA = "{}/chains/main/blocks/{}/metadata"
COMM_SNAPSHOT = COMM_BLOCK + "/context/selected_snapshot"
COMM_DELEGATE_BALANCE = "{}/chains/main/blocks/{}/context/contracts/{}/balance"
COMM_CONTRACT_STORAGE = "{}/chains/main/blocks/{}/context/contracts/{}/storage"
COMM_BIGMAP_QUERY = "{}/chains/main/blocks/{}/context/big_maps/{}/{}"
# max rounds set to 2; will scan for stolen blocks up to this round
COMM_BAKING_RIGHTS = (
    "{}/chains/main/blocks/{}/helpers/baking_rights?cycle={}&delegate={}&max_round=2"
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
        self.blocks_per_stake_snapshot = nw["BLOCKS_PER_STAKE_SNAPSHOT"]
        self.block_reward = nw["BLOCK_REWARD"]

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

            # Get last block in cycle, where endorsement rewards are distributed by the proto
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
                    cycle + 1
                ) * BLOCKS_PER_CYCLE_BEFORE_GRANADA
                level_of_first_block_in_preserved_cycles = (
                    cycle - self.preserved_cycles
                ) * BLOCKS_PER_CYCLE_BEFORE_GRANADA + 1

            logger.debug(
                "Cycle {:d}, blocks per cycle {:d}, last block of cycle {:d}".format(
                    cycle,
                    self.blocks_per_cycle,
                    level_of_last_block_in_unfreeze_cycle,
                )
            )

            # Determine how many round 0 baking rights delegate had
            baking_rights = self.__get_baking_rights(
                cycle, level_of_first_block_in_preserved_cycles
            )
            nb_blocks = len([r for r in baking_rights if r["round"] == 0])

            total_reward_amount = None
            if not rewards_type.isEstimated():
                # Calculate actual rewards
                endorsing_rewards, lost_endorsing_rewards = self.__get_endorsing_rewards(
                    level_of_last_block_in_unfreeze_cycle, cycle
                )
                total_reward_amount = endorsing_rewards

            # Without an indexer, it is not possible to itemize rewards
            # so setting these values below to "None"
            rewards_and_fees = None
            equivocation_losses = None
            denunciation_rewards = None

            offline_losses = None
            missed_baking_income = 0
            for count, r in enumerate(baking_rights):
                if count % 10 == 0:
                    logger.info(
                        "Scanning blocks ({}/{}).".format(count, len(baking_rights))
                    )
                block_author, block_payload_proposer, block_reward_and_fees, block_bonus = self.__get_block_metadata(r['level'])
                if block_author == self.baking_address:
                    if r["round"] != 0:
                        logger.info(
                            "Found stolen baking slot {}.".format(
                                r
                            )
                        )
                    if block_payload_proposer != self.baking_address:
                        logger.warning(
                            "We are block proposer ({}) but not payload proposer ({}) for block  {}.".format(
                                r,
                                self.baking_address,
                                block_payload_proposer
                            )
                        )
                else:
                    if r["round"] == 0:
                        logger.warning(
                            "Found missed baking slot {}.".format(
                                r
                            )
                        )

            offline_losses = missed_baking_income

            nb_endorsements = 0
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

    def __get_response(self, address, request, response=None):
        retry_count = 0
        while (not response) and (retry_count < MAX_SEQUENT_CALLS):
            retry_count += 1
            sleep(RPC_REQUEST_BUFFER_SECONDS)  # Be nice to public RPC
            try:
                logger.info("Fetching address {:s} ...".format(address))
                response = self.do_rpc_request(request, time_out=5)
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

    def __get_block_metadata(self, level):
        """
        Returns baker public key hash for a given block level.
        """

        try:
            block_metadata_rpc = COMM_BLOCK_METADATA.format(self.node_url, level)
            response = self.do_rpc_request(block_metadata_rpc)
            author = response["baker"]
            reward_and_fees = bonus = 0
            balance_updates = response["balance_updates"]
            for i, bu in enumerate(balance_updates):
                if bu["kind"] == "contract":
                    if balance_updates[i - 1]["category"] == "baking rewards":
                        payload_proposer = bu["contract"] # author of the block payload (not necessarily block producer)
                        reward_and_fees = int(bu["change"])
                    if balance_updates[i - 1]["category"] == "baking bonuses":
                        bonus = int(bu["change"])

            return author, payload_proposer, reward_and_fees, bonus


        except ApiProviderException as e:
            raise e from e

    def __get_endorsing_rewards(self, level_of_last_block_in_unfreeze_cycle, cycle):
        request_metadata = (
            COMM_BLOCK.format(self.node_url, level_of_last_block_in_unfreeze_cycle)
            + "/metadata"
        )
        metadata = self.do_rpc_request(request_metadata)
        balance_updates = metadata["balance_updates"]
        endorsing_rewards = lost_endorsing_rewards = 0

        for i in range(len(balance_updates)):
            balance_update = balance_updates[i]
            if balance_update["kind"] == "contract" and \
                balance_update["contract"] == self.baking_address and \
                balance_updates[i - 1]["kind"] == "minted" and \
                balance_updates[i - 1]["category"] == "endorsing rewards" and \
                int(balance_updates[i - 1]["change"]) == - int(balance_update["change"]):

                endorsing_rewards = int(balance_update["change"])
                logger.info(f"Found endorsing rewards of {endorsing_rewards}")
            elif balance_update["kind"] == "burned" and \
                "contract" in balance_update and \
                balance_update["contract"] == self.baking_address and \
                balance_update["category"] == "lost endorsing rewards":
                lost_endorsing_rewards = int(balance_update["change"])
                logger.info(f"Found lost endorsing reward of {lost_endorsing_rewards}")


        return endorsing_rewards, lost_endorsing_rewards

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
        # FIXME replace "head" with the block we actually need
        get_delegates_request = COMM_DELEGATES.format(
            self.node_url, "head", self.baking_address
        )

        # get RPC response for delegates and staking balance
        response = self.do_rpc_request(get_delegates_request)
        delegate_staking_balance = int(response["staking_balance"])
        all_delegates = []
        for pkh in response["delegated_contracts"]:
            get_pk = COMM_MANAGER_KEY.format(self.node_url, "head", pkh)
            all_delegates.append(self.do_rpc_request(get_pk))

        delegate_staking_balance = 0
        d_a_len = 0
        delegators = {}

        try:
            # get RPC response for delegates and staking balance
            response = self.do_rpc_request(get_delegates_request)
            delegate_staking_balance = int(response["staking_balance"])

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
                d_info["staking_balance"] = int(
                    self.__get_response(delegator, get_staking_balance_request)
                )

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
            request = COMM_SNAPSHOT.format(self.node_url, "head")
            chosen_snapshot = self.do_rpc_request(request)

            if cycle >= FIRST_CYCLE_SNAPSHOT_GRANADA:
                # Using an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
                level_snapshot_block = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles - 2)
                    * self.blocks_per_cycle
                    + (chosen_snapshot + 1) * self.blocks_per_stake_snapshot
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
