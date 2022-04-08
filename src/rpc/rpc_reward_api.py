from time import sleep
import json
import math

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
COMM_SNAPSHOT = COMM_BLOCK + "/context/selected_snapshot?cycle={}"
COMM_DELEGATE_BALANCE = "{}/chains/main/blocks/{}/context/contracts/{}/balance"
# max rounds set to 2; will scan for stolen blocks up to this round
COMM_BAKING_RIGHTS = (
    "{}/chains/main/blocks/{}/helpers/baking_rights?cycle={}&delegate={}&max_round=2"
)
COMM_SELECTED_STAKE_DISTRIBUTION = (
    "{}/chains/main/blocks/{}/context/raw/json/cycle/{}/selected_stake_distribution"
)
COMM_TOTAL_ACTIVE_STAKE = (
    "{}/chains/main/blocks/{}/context/raw/json/cycle/{}/total_active_stake"
)

# Constants used for mainnet calculations related to the cycles before Granada
CYCLES_BEFORE_GRANADA = 388
BLOCKS_BEFORE_GRANADA = 1589248

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
        self.network = nw["NAME"]
        self.consensus_committee_size = nw["CONSENSUS_COMMITTEE_SIZE"]
        self.endorsing_reward_per_slot = nw["ENDORSING_REWARD_PER_SLOT"]

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

            # Get last block in cycle, where endorsement rewards are distributed by the proto
            if self.network == "MAINNET":
                # Calculating the cycle from level is special on mainnet.
                # Mainnet's blocks per cycles have changed during granada migration.
                # Since cycle 394, we use an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
                # Cycles start at 0
                level_of_last_block_in_cycle = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA + 1) * self.blocks_per_cycle
                )
                snapshot_cycle_first_block_level = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles)
                    * self.blocks_per_cycle
                    + 1
                )
                # FIXME special case for tenderbake activation: we normally query rights at the first block right after they were calculated
                # technically PRESERVED_CYCLES before the cycle.
                # But for tenderbake activation, we calculated 6 cycles in one go
                # It's safe to remove the statment below once we are past this inital phase.
                if cycle < 474:
                    snapshot_cycle_first_block_level = 2264608
                # end ithaca special
            else:
                # Testnets
                level_of_last_block_in_cycle = (cycle + 1) * self.blocks_per_cycle
                snapshot_cycle_first_block_level = (
                    cycle - self.preserved_cycles
                ) * self.blocks_per_cycle + 1
            logger.debug(
                f"We are on {self.network}, last block in cycle {cycle} is {level_of_last_block_in_cycle}."
            )
            logger.debug(
                f"First block in snapshotting cycle {cycle - self.preserved_cycles - 1} is {snapshot_cycle_first_block_level}."
            )

            logger.debug(
                "Cycle {:d}, blocks per cycle {:d}, last block of cycle {:d}".format(
                    cycle,
                    self.blocks_per_cycle,
                    level_of_last_block_in_cycle,
                )
            )

            potential_endorsement_rewards = self.__get_potential_endorsement_rewards(
                cycle, snapshot_cycle_first_block_level
            )

            reward_data = {}
            (
                reward_data["delegate_staking_balance"],
                reward_data["delegators"],
            ) = self.__get_delegators_and_delgators_balances(cycle, current_level)
            reward_data["delegators_nb"] = len(reward_data["delegators"])

            # Collect baking rights
            baking_rights = self.__get_baking_rights(
                cycle, snapshot_cycle_first_block_level
            )
            nb_endorsements = 0
            nb_blocks = len([r for r in baking_rights if r["round"] == 0])
            logger.info(
                f"Baker has rights to perform {nb_blocks:<,d} bakes for this cycle."
            )

            total_block_rewards_and_fees = 0
            total_block_bonus = 0

            # scanning for equivocation losses is not supported in RPC
            # this would require scanning every block
            equivocation_losses = 0

            if rewards_type.isEstimated():
                # we can't calculate this yet, cycle hasn't run
                denunciation_rewards = None
                offline_losses = None
                endorsing_rewards = None
                rewards_and_fees = None
                total_reward_amount = None
            else:
                denunciation_rewards = 0
                offline_losses = 0

                # Calculate actual rewards - cycle must have run
                (
                    endorsing_rewards,
                    lost_endorsing_rewards,
                ) = self.__get_endorsing_rewards(level_of_last_block_in_cycle, cycle)
                offline_losses += lost_endorsing_rewards

                for count, r in enumerate(baking_rights):
                    if count % 10 == 0:
                        logger.info(
                            "Scanning blocks ({}/{}).".format(count, len(baking_rights))
                        )
                    (
                        block_author,
                        block_payload_proposer,
                        block_reward_and_fees,
                        block_bonus,
                        block_double_signing_reward,
                    ) = self.__get_block_data(r["level"])
                    if block_author == self.baking_address:
                        # we are block proposer for this block
                        total_block_bonus += block_bonus
                        if r["round"] != 0:
                            logger.info(
                                "Found stolen baking slot at level {}, round {}.".format(
                                    r["level"], r["round"]
                                )
                            )
                        if block_payload_proposer != self.baking_address:
                            logger.info(
                                "We are block proposer ({}) but not payload proposer ({}) for block level {}, round {}.".format(
                                    self.baking_address,
                                    block_payload_proposer,
                                    r["level"],
                                    r["round"],
                                )
                            )
                    else:
                        # we are not block proposer for this block
                        if r["round"] == 0:
                            logger.warning("Found missed baking slot {}.".format(r))
                            offline_losses += block_bonus + block_reward_and_fees
                    if block_payload_proposer == self.baking_address:
                        # note: this may also happen when we missed the block. In this case, it's not our fault and should not go to ideal.
                        total_block_rewards_and_fees += block_reward_and_fees
                    denunciation_rewards += block_double_signing_reward

                logger.info(
                    f"Total payload producer's reward for baker: {total_block_rewards_and_fees:<,d} mutez."
                )
                logger.info(
                    f"Total block producer's bonus for baker: {total_block_bonus:<,d} mutez."
                )

                logger.info(
                    f"Total block reward for baker (sum of 2 values above): {(total_block_rewards_and_fees + total_block_bonus):<,d} mutez."
                )
                logger.info(
                    f"Total denunciation reward is: {denunciation_rewards:<,d} mutez."
                )

                rewards_and_fees = (
                    total_block_rewards_and_fees + total_block_bonus + endorsing_rewards
                )

                total_reward_amount = rewards_and_fees + denunciation_rewards

            reward_model = RewardProviderModel(
                reward_data["delegate_staking_balance"],
                nb_blocks,
                potential_endorsement_rewards,
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
                logger.debug("Fetching address {:s} ...".format(address))
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

    def __get_potential_endorsement_rewards(self, cycle, level):
        """
        In tenderbake, endorsement rewards are calculated based on stake for a cycle.
        Then there are either fully paid, or not at all.
        We calculate this potential amount. It is possible to calculate it for future cycles.
        """

        try:
            number_of_endorsements_per_cycle = (
                self.blocks_per_cycle * self.consensus_committee_size
            )
            total_active_stake_rpc = COMM_TOTAL_ACTIVE_STAKE.format(
                self.node_url, level, cycle
            )
            total_active_stake = int(self.do_rpc_request(total_active_stake_rpc))
            selected_stake_distribution_rpc = COMM_SELECTED_STAKE_DISTRIBUTION.format(
                self.node_url, level, cycle
            )
            selected_stake_distribution = self.do_rpc_request(
                selected_stake_distribution_rpc
            )
            delegate_stake = [
                int(ssd["active_stake"])
                for ssd in selected_stake_distribution
                if ssd["baker"] == self.baking_address
            ][0]
            return (
                math.floor(
                    delegate_stake
                    * number_of_endorsements_per_cycle
                    / total_active_stake
                )
                * self.endorsing_reward_per_slot
            )

        except ApiProviderException as e:
            raise e from e

    def __get_block_data(self, level):
        """
        Returns baker relevant reward data for a given block level.
        """

        try:
            block_rpc = COMM_BLOCK.format(self.node_url, level)
            response = self.do_rpc_request(block_rpc)
            metadata = response["metadata"]
            author = metadata["baker"]
            reward_and_fees = bonus = 0
            balance_updates = metadata["balance_updates"]
            for i, bu in enumerate(balance_updates):
                if bu["kind"] == "contract" and "category" in balance_updates[i - 1]:
                    if balance_updates[i - 1]["category"] == "baking rewards":
                        payload_proposer = bu[
                            "contract"
                        ]  # author of the block payload (not necessarily block producer)
                        reward_and_fees = int(bu["change"])
                    if balance_updates[i - 1]["category"] == "baking bonuses":
                        bonus = int(bu["change"])

            operations = response["operations"][2]
            double_signing_reward = 0
            for op in operations:
                for content in op["contents"]:
                    balance_updates = content["metadata"]["balance_updates"]
                    for i, bu in enumerate(balance_updates):
                        if (
                            bu["kind"] == "contract"
                            and bu["contract"] == self.baking_address
                        ):
                            if (
                                balance_updates[i - 1]["category"]
                                == "double signing evidence rewards"
                            ):
                                logger.info(
                                    f"Delegate submitted double signing evidence and earned a reward of {bu['change']}"
                                )
                                double_signing_reward += int(bu["change"])
                            elif (
                                balance_updates[i - 1]["category"]
                                == "nonce revelation rewards"
                            ):
                                logger.info(
                                    f"Delegate submitted a nonce revelation and earned a reward of {bu['change']}"
                                )
                                reward_and_fees += int(bu["change"])

            return (
                author,
                payload_proposer,
                reward_and_fees,
                bonus,
                double_signing_reward,
            )

        except ApiProviderException as e:
            raise e from e

    def __get_endorsing_rewards(self, level_of_last_block_in_cycle, cycle):
        request_metadata = (
            COMM_BLOCK.format(self.node_url, level_of_last_block_in_cycle) + "/metadata"
        )
        metadata = self.do_rpc_request(request_metadata)
        balance_updates = metadata["balance_updates"]
        endorsing_rewards = lost_endorsing_rewards = 0

        for i in range(len(balance_updates)):
            balance_update = balance_updates[i]
            if (
                balance_update["kind"] == "contract"
                and balance_update["contract"] == self.baking_address
                and balance_updates[i - 1]["kind"] == "minted"
                and balance_updates[i - 1]["category"] == "endorsing rewards"
                and int(balance_updates[i - 1]["change"])
                == -int(balance_update["change"])
            ):

                endorsing_rewards = int(balance_update["change"])
                logger.info(f"Found endorsing rewards of {endorsing_rewards}")
            elif (
                balance_update["kind"] == "burned"
                and "contract" in balance_update
                and balance_update["contract"] == self.baking_address
                and balance_update["category"] == "lost endorsing rewards"
            ):
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

    def __get_current_level(self):
        head = self.do_rpc_request(COMM_HEAD.format(self.node_url))
        current_level = int(head["metadata"]["level_info"]["level"])
        current_cycle = int(head["metadata"]["level_info"]["cycle"])

        return current_level, current_cycle

    def __get_delegators_and_delgators_balances(
        self, cycle, snapshot_cycle_first_block_level
    ):

        # calculate the hash of the block for the chosen snapshot of the rewards cycle
        stake_snapshot, level_snapshot_block = self.__get_stake_snapshot_block_level(
            cycle, snapshot_cycle_first_block_level
        )
        if level_snapshot_block == "":
            raise ApiProviderException(
                "[get_d_d_b] level_snapshot_block is empty. Unable to proceed."
            )
        if stake_snapshot < 0 or stake_snapshot > 15:
            raise ApiProviderException(
                "[get_d_d_b] stake_snapshot is outside allowable range: {} Unable to proceed.".format(
                    stake_snapshot
                )
            )
        # construct RPC for getting list of delegates and staking balance
        get_delegates_request = COMM_DELEGATES.format(
            self.node_url, level_snapshot_block, self.baking_address
        )

        # get RPC response for delegates and staking balance
        response = self.do_rpc_request(get_delegates_request)
        delegate_staking_balance = int(response["staking_balance"])

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

    def __get_stake_snapshot_block_level(self, cycle, query_level):
        logger.info(
            "The reward cycle is {}, level used to query context for the snapshot level is {}".format(
                cycle, query_level
            )
        )

        if self.network == "MAINNET":
            if cycle in range(468, 474):
                # cycle 468-473 are special
                # immediately after ithaca activation, we are using the same snapshot for 5 cycles
                chosen_snapshot = 0
                level_snapshot_block = 2244608
                logger.info(
                    "ITHACA ACTIVATION SPECIAL: The snapshot index {} was used to calculate rewards for cycle {}, so we will be querying balances for level {}".format(
                        chosen_snapshot, cycle, level_snapshot_block
                    )
                )

                return chosen_snapshot, level_snapshot_block
            if cycle == 474:
                # cycle 474 is special as well
                # source: baking slack https://tezos-baking.slack.com/archives/CC4FD2HUY/p1649171746418819?thread_ts=1649147045.126789&cid=CC4FD2HUY
                chosen_snapshot = 15
                level_snapshot_block = 2252800
                logger.info(
                    "ITHACA ACTIVATION SPECIAL: The snapshot index {} was used to calculate rewards for cycle {}, so we will be querying balances for level {}".format(
                        chosen_snapshot, cycle, level_snapshot_block
                    )
                )

                return chosen_snapshot, level_snapshot_block

        request = COMM_SNAPSHOT.format(self.node_url, query_level, cycle)
        chosen_snapshot = self.do_rpc_request(request)

        if self.network == "MAINNET":
            # Using an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
            level_snapshot_block = BLOCKS_BEFORE_GRANADA + (
                (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles - 1)
                * self.blocks_per_cycle
                + (chosen_snapshot + 1) * self.blocks_per_stake_snapshot
            )
        else:
            # testnet has no offset
            level_snapshot_block = (
                cycle - self.preserved_cycles - 1
            ) * self.blocks_per_cycle + (
                chosen_snapshot + 1
            ) * self.blocks_per_stake_snapshot

        logger.info(
            "The snapshot index {} was used to calculate rewards for cycle {}, so we will be querying balances for level {}".format(
                chosen_snapshot, cycle, level_snapshot_block
            )
        )

        return chosen_snapshot, level_snapshot_block
