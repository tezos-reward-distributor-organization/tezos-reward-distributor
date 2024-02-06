from time import sleep
import math

import requests
from http import HTTPStatus

from api.reward_api import RewardApi
from exception.api_provider import ApiProviderException
from log_config import main_logger, verbose_logger
from model.reward_provider_model import RewardProviderModel
from Constants import MAX_SEQUENT_CALLS

logger = main_logger.getChild("rpc_reward_api")

# RPC constants
COMM_BLOCK = "{}/chains/main/blocks/{}"
COMM_HEAD = "{}/chains/main/blocks/head"
COMM_DELEGATES = COMM_BLOCK + "/context/delegates/{}"
COMM_SNAPSHOT_TENDERBAKE = COMM_BLOCK + "/context/selected_snapshot?cycle={}"
COMM_SNAPSHOT = COMM_BLOCK + "/context/raw/json/cycle/{}/roll_snapshot"
COMM_DELEGATE_BALANCE = COMM_BLOCK + "/context/contracts/{}/balance"
COMM_CONTRACT_STORAGE = "{}/chains/main/blocks/{}/context/contracts/{}/storage"
# max rounds set to 2; will scan for stolen blocks up to this round
COMM_ALL_BAKING_RIGHTS_HEAD = COMM_BLOCK + "/helpers/baking_rights"
COMM_ALL_BAKING_RIGHTS_CYCLE = COMM_ALL_BAKING_RIGHTS_HEAD + "?cycle={}"
COMM_BAKING_RIGHTS = COMM_ALL_BAKING_RIGHTS_HEAD + "?delegate={}&cycle={}&max_round=2"
COMM_SELECTED_STAKE_DISTRIBUTION = (
    COMM_BLOCK + "/context/raw/json/cycle/{}/selected_stake_distribution"
)
COMM_TOTAL_ACTIVE_STAKE = (
    COMM_BLOCK + "/context/raw/json/cycle/{}/total_active_stake"
)  # available since cycle 467 block 2244608

# Constants used for mainnet calculations related to the cycles before Granada
CYCLES_BEFORE_GRANADA = 388
FIRST_CYCLE_REWARDS_GRANADA = CYCLES_BEFORE_GRANADA + 6
FIRST_CYCLE_SNAPSHOT_GRANADA = FIRST_CYCLE_REWARDS_GRANADA + 2
BLOCKS_PER_CYCLE_BEFORE_GRANADA = 4096
BLOCKS_BEFORE_GRANADA = 1589248
CYCLES_BEFORE_TENDERBAKE = 467
BLOCKS_BEFORE_TENDERBAKE = 2244608

RPC_REQUEST_BUFFER_SECONDS = 0.4
RPC_RETRY_TIMEOUT_SECONDS = 2.0


class RpcRewardApiImpl(RewardApi):
    def __init__(self, nw, baking_address, node_url):
        super(RpcRewardApiImpl, self).__init__()

        self.name = "RPC"

        self.blocks_per_cycle = nw["BLOCKS_PER_CYCLE"]
        self.preserved_cycles = nw["PRESERVED_CYCLES"]
        self.blocks_per_stake_snapshot = nw["BLOCKS_PER_STAKE_SNAPSHOT"]
        self.block_reward = nw["BLOCK_REWARD"]
        self.network = nw["NAME"]
        self.consensus_committee_size = nw["CONSENSUS_COMMITTEE_SIZE"]
        self.endorsing_reward_per_slot = nw["ENDORSING_REWARD_PER_SLOT"]

        self.baking_address = baking_address
        self.node_url = node_url

    def get_levels(self, cycle, network="MAINNET"):
        # Get last block in cycle, where endorsement rewards are distributed by the proto
        if network == "MAINNET":
            # Calculating the cycle from level is special on mainnet.
            # Mainnet's blocks per cycles have changed during granada migration.
            # Since cycle 394, we use an offset of 1589248 blocks (388 cycles pre-Granada of 4096 blocks each)
            # Cycles start at 0
            if cycle >= FIRST_CYCLE_REWARDS_GRANADA:
                level_of_last_block_in_cycle = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA + 1) * self.blocks_per_cycle
                )
                snapshot_cycle_first_block_level = BLOCKS_BEFORE_GRANADA + (
                    (cycle - CYCLES_BEFORE_GRANADA - self.preserved_cycles)
                    * self.blocks_per_cycle
                    + 1
                )
            else:
                # Using pre-Granada calculation
                snapshot_cycle_first_block_level = (
                    cycle * BLOCKS_PER_CYCLE_BEFORE_GRANADA + 1
                )
                level_of_last_block_in_cycle = cycle * BLOCKS_PER_CYCLE_BEFORE_GRANADA
        else:
            # Testnets
            level_of_last_block_in_cycle = (cycle + 1) * self.blocks_per_cycle
            snapshot_cycle_first_block_level = (
                cycle - self.preserved_cycles
            ) * self.blocks_per_cycle + 1
        logger.debug(
            f"We are on {network}, last block in cycle {cycle} is {level_of_last_block_in_cycle}."
        )
        logger.debug(
            f"First block in snapshotting cycle {cycle - self.preserved_cycles} is {snapshot_cycle_first_block_level}."
        )

        logger.debug(
            "Cycle {:d}, blocks per cycle {:d}, last block of cycle {:d}".format(
                cycle,
                self.blocks_per_cycle,
                level_of_last_block_in_cycle,
            )
        )
        return level_of_last_block_in_cycle, snapshot_cycle_first_block_level

    def get_rewards_for_cycle_map(self, cycle, rewards_type):
        rights_name = "priority" if cycle < CYCLES_BEFORE_TENDERBAKE else "round"
        try:
            current_level, current_cycle = self.get_current_level()
            logger.debug(
                "Current level {:d}, current cycle {:d}".format(
                    current_level, current_cycle
                )
            )

            (
                level_of_last_block_in_cycle,
                snapshot_cycle_first_block_level,
            ) = self.get_levels(cycle, self.network)

            potential_endorsement_rewards = self.get_potential_endorsement_rewards(
                cycle, current_level
            )

            reward_data = {}
            (
                reward_data["delegate_staking_balance"],
                reward_data["delegators"],
            ) = self.get_delegators_and_delgators_balances(current_level)
            reward_data["delegators_nb"] = len(reward_data["delegators"])

            # Collect baking rights
            baking_rights = self.get_baking_rights(cycle, self.baking_address)
            ensured_baking_rights = [
                right for right in baking_rights if right[rights_name] == 0
            ]
            nb_blocks = len(ensured_baking_rights)
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
                ) = self.get_endorsing_rewards(level_of_last_block_in_cycle)
                offline_losses += lost_endorsing_rewards

                for count, baking_right in enumerate(ensured_baking_rights):
                    if count % 10 == 0:
                        logger.info(
                            "Scanning blocks ({}/{}).".format(
                                count, len(ensured_baking_rights)
                            )
                        )
                    (
                        block_author,
                        block_payload_proposer,
                        block_reward_and_fees,
                        block_bonus,
                        block_double_signing_reward,
                    ) = self.get_block_data(baking_right["level"])
                    if block_author == self.baking_address:
                        # we are block proposer for this block
                        total_block_bonus += block_bonus
                        if baking_right[rights_name] != 0:
                            logger.info(
                                "Found stolen baking slot at level {}, round {}.".format(
                                    baking_right["level"], baking_right[rights_name]
                                )
                            )
                        if block_payload_proposer != self.baking_address:
                            logger.info(
                                "We are block proposer ({}) but not payload proposer ({}) for block level {}, round {}.".format(
                                    self.baking_address,
                                    block_payload_proposer,
                                    baking_right["level"],
                                    baking_right[rights_name],
                                )
                            )
                    else:
                        # we are not block proposer for this block
                        if baking_right[rights_name] == 0:
                            logger.warning(
                                "Found missed baking slot {}.".format(baking_right)
                            )
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

    def get_response(self, address, request, response=None):
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

    def get_baking_rights(self, cycle, baking_address):
        """
        Returns list of baking rights for a given cycle.
        """
        baking_rights_rpc = COMM_BAKING_RIGHTS.format(
            self.node_url, "head", baking_address, cycle
        )
        try:
            backing_rights = self.do_rpc_request(baking_rights_rpc)
        except ApiProviderException as e:
            raise e from e
        return backing_rights

    def get_all_baking_rights(self, level):
        all_baking_rights_rpc = COMM_ALL_BAKING_RIGHTS_HEAD.format(self.node_url, level)
        try:
            all_backing_rights = self.do_rpc_request(all_baking_rights_rpc)
        except ApiProviderException as e:
            raise e from e
        return all_backing_rights

    def get_all_baking_rights_cycle(self, cycle):
        all_baking_rights_cycle_rpc = COMM_ALL_BAKING_RIGHTS_CYCLE.format(
            self.node_url, "head", cycle
        )
        try:
            all_backing_rights_cycle = self.do_rpc_request(all_baking_rights_cycle_rpc)
        except ApiProviderException as e:
            raise e from e
        return all_backing_rights_cycle

    def get_potential_endorsement_rewards(self, cycle, level):
        """
        In tenderbake, endorsement rewards are calculated based on stake for a cycle.
        Then there are either fully paid, or not at all.
        We calculate this potential amount. It is possible to calculate it for future cycles.
        """

        # NOTE: The tenderbake specific RPC query cannot query below the block level 2244608 and below cycle 467
        if (
            level != "head"
            and level < BLOCKS_BEFORE_TENDERBAKE
            or cycle < CYCLES_BEFORE_TENDERBAKE
        ):
            logger.warning(
                "ITHACA SPECIAL: RPC cannot query total_active_stake below the block level 2244608 and below cycle 467. Setting potential_endorsement_rewards to 0."
            )
            return 0

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
            ]

            if len(delegate_stake) == 0:
                return 0
            delegate_stake = delegate_stake[0]  # unlist

            # https://tezos-dev.slack.com/archives/CV5NX7F2L/p1649433246273169?thread_ts=1648854391.875409&cid=CV5NX7F2L
            potential_endorsement_rewards = (
                math.floor(
                    delegate_stake
                    * number_of_endorsements_per_cycle
                    / total_active_stake
                )
                * self.endorsing_reward_per_slot
            )
            return potential_endorsement_rewards

        except ApiProviderException as e:
            raise e from e

    def get_block_data(self, level):
        """
        Returns baker relevant reward data for a given block level.
        """

        try:
            block_rpc = COMM_BLOCK.format(self.node_url, level)
            response = self.do_rpc_request(block_rpc)
            metadata = response["metadata"]
            author = metadata["baker"]
            reward_and_fees = bonus = double_signing_reward = 0
            balance_updates = metadata["balance_updates"]
            for i, balance_update in enumerate(balance_updates):
                if (
                    balance_update["kind"] == "contract"
                    and "category" in balance_updates[i - 1]
                ):
                    if balance_updates[i - 1]["category"] in [
                        "baking rewards",
                        "rewards",
                    ]:
                        payload_proposer = balance_update[
                            "contract"
                        ]  # author of the block payload (not necessarily block producer)
                        reward_and_fees = int(balance_update["change"])
                    if balance_updates[i - 1]["category"] == "baking bonuses":
                        bonus = int(balance_update["change"])

            operations = response["operations"][2]
            for operation in operations:
                for content in operation["contents"]:
                    balance_updates = content["metadata"]["balance_updates"]
                    for i, balance_update in enumerate(balance_updates):
                        if (
                            balance_update["kind"] == "contract"
                            and balance_update["contract"] == self.baking_address
                        ):
                            if (
                                balance_updates[i - 1]["category"]
                                == "double signing evidence rewards"
                            ):
                                logger.info(
                                    f"Delegate submitted double signing evidence and earned a reward of {balance_update['change']}"
                                )
                                double_signing_reward += int(balance_update["change"])
                            elif (
                                balance_updates[i - 1]["category"]
                                == "nonce revelation rewards"
                            ):
                                logger.info(
                                    f"Delegate submitted a nonce revelation and earned a reward of {balance_update['change']}"
                                )
                                reward_and_fees += int(balance_update["change"])

            return (
                author,
                payload_proposer,
                reward_and_fees,
                bonus,
                double_signing_reward,
            )

        except ApiProviderException as e:
            raise e from e

    def get_endorsing_rewards(self, level_of_last_block_in_cycle):
        endorsing_rewards = lost_endorsing_rewards = 0
        request_metadata = (
            COMM_BLOCK.format(self.node_url, level_of_last_block_in_cycle) + "/metadata"
        )

        try:
            metadata = self.do_rpc_request(request_metadata)
        except ApiProviderException:
            # If metadata is not available return zeros
            return endorsing_rewards, lost_endorsing_rewards

        if (
            isinstance(list, type(metadata))
            and "block_metadata_not_found" in metadata[0]
        ):
            logger.warning("Block metadata not found!")
            return endorsing_rewards, lost_endorsing_rewards

        balance_updates = metadata["balance_updates"]

        for i, balance_update in enumerate(balance_updates):
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
            else:
                logger.info("No endorsing rewards found ...")

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
                rl.current_balance = self.get_current_balance_of_delegator(rl.address)
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
        return self.get_response(contract_id, get_contract_storage_request)

    def get_contract_balance(self, contract_id, block):
        get_contract_balance_request = COMM_DELEGATE_BALANCE.format(
            self.node_url, block, contract_id
        )
        return int(self.get_response(contract_id, get_contract_balance_request))

    def get_current_level(self):
        head = self.do_rpc_request(COMM_HEAD.format(self.node_url))
        current_level = int(head["metadata"]["level_info"]["level"])
        current_cycle = int(head["metadata"]["level_info"]["cycle"])

        return current_level, current_cycle

    def get_delegators_and_delgators_balances(self, snapshot_cycle_first_block_level):
        # construct RPC for getting list of delegates and staking balance
        get_delegates_request = COMM_DELEGATES.format(
            self.node_url, snapshot_cycle_first_block_level, self.baking_address
        )
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
            for idx, delegator in enumerate(delegators_addresses, start=1):
                # create new dictionary for each delegator
                d_info = {"staking_balance": 0, "current_balance": 0}
                d_info["staking_balance"] = self.get_contract_balance(
                    delegator, snapshot_cycle_first_block_level
                )

                # Ignore delegators who have zero staking balance
                # since they are not relevant for reward calculations
                if not d_info["staking_balance"] > 0:
                    d_a_len -= 1  # decrement the sanity check count
                    logger.debug(
                        "Ignoring delegator {} with zero staking balance!".format(
                            delegator
                        )
                    )
                    continue

                sleep(
                    0.5
                )  # Be nice to public RPC since we are now making 2x the amount of RPC calls

                d_info["current_balance"] = self.get_current_balance_of_delegator(
                    delegator
                )

                logger.debug(
                    "Delegator info ({}/{}) fetched: address {}, staked balance {}, current balance {} ".format(
                        idx,
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

    def get_current_balance_of_delegator(self, address):
        """Helper function to get current balance of delegator"""
        return self.get_contract_balance(address, "head")
