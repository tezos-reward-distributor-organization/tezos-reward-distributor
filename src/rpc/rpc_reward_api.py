from api.reward_api import RewardApi

from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from cli.cmd_manager import CommandManager
from util.rpc_utils import parse_json_response, extract_json_part

logger = main_logger

COMM_HEAD = " rpc get http://{}/chains/main/blocks/head"
COMM_DELEGATES = " rpc get http://{}/chains/main/blocks/{}/context/delegates/{}"
COMM_BLOCK = " rpc get http://{}/chains/main/blocks/{}/"
COMM_SNAPSHOT = COMM_BLOCK + "context/raw/json/rolls/owner/snapshot/{}/"
COMM_DELEGATE_BALANCE = " rpc get http://{}/chains/main/blocks/{}/context/contracts/{}"

class RpcRewardApiImpl(RewardApi):

    def __init__(self, nw, baking_address, wllt_clnt_mngr, node_url, validate=True):
        super(RpcRewardApiImpl, self).__init__()

        self.blocks_per_cycle = nw['BLOCKS_PER_CYCLE']
        self.preserved_cycles = nw['NB_FREEZE_CYCLE']
        self.blocks_per_roll_snapshot = nw['BLOCKS_PER_ROLL_SNAPSHOT']

        self.baking_address = baking_address
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.node_url = node_url

        self.validate = validate

    def get_nb_delegators(self, cycle, verbose=False):
        _, delegators = self.__get_delegators_and_delgators_balance(cycle,verbose )
        return len(delegators)

    def get_rewards_for_cycle_map(self, cycle, verbose=False):

        reward_data = {}

        reward_data["delegate_staking_balance"], reward_data[
            "delegators"] = self.__get_delegators_and_delgators_balance(cycle, verbose)
        reward_data["delegators_nb"] = len(reward_data["delegators"])

        current_level, head_hash, current_cycle = self.__get_current_level(verbose)

        logger.debug("Current level {}, head hash {}".format(current_level, head_hash))

        # Get last block in cycle where rewards are unfrozen
        level_for_relevant_request = (cycle + self.preserved_cycles + 1) * self.blocks_per_cycle

        logger.debug("Cycle {}, preserved cycles {}, blocks per cycle {}, level of interest {}"
                     .format(cycle, self.preserved_cycles, self.blocks_per_cycle, level_for_relevant_request))

        if current_level - level_for_relevant_request >= 0:
            request_metadata = COMM_BLOCK.format(self.node_url, head_hash,
                                                 current_level - level_for_relevant_request) + '/metadata/'
            _, response_metadata = self.wllt_clnt_mngr.send_request(request_metadata)
            metadata = parse_json_response(response_metadata)
            balance_updates = metadata["balance_updates"]

            unfrozen_rewards = unfrozen_fees = 0
            for i in range(len(balance_updates)):
                balance_update = balance_updates[i]
                if balance_update["kind"] == "freezer":
                    if balance_update["delegate"] == self.baking_address:
                        if balance_update["category"] == "rewards":
                            unfrozen_rewards = -int(balance_update["change"])
                        elif balance_update["category"] == "fees":
                            unfrozen_fees = -int(balance_update["change"])
            reward_data["total_rewards"] = unfrozen_rewards + unfrozen_fees

        else:
            logger.warn("Please wait until the rewards and fees for cycle {} are unfrozen".format(cycle))
            reward_data["total_rewards"] = 0

        reward_model = RewardProviderModel(reward_data["delegate_staking_balance"], reward_data["total_rewards"],
                                           reward_data["delegators"])

        if self.validate:
            self.__validate_reward_data(reward_model, cycle)

        return reward_model

    def __get_current_level(self, verbose=False):
        _, response = self.wllt_clnt_mngr.send_request(COMM_HEAD.format(self.node_url))
        head = parse_json_response(response)
        current_level = int(head["metadata"]["level"]["level"])
        current_cycle = int(head["metadata"]["level"]["cycle"])
        head_hash = head["hash"]
        return current_level, head_hash, current_cycle

    def __get_delegators_and_delgators_balance(self, cycle, verbose=False):

        hash_snapshot_block = self.__get_snapshot_block_hash(cycle)
        if hash_snapshot_block == "":
            return 0, []

        request = COMM_DELEGATES.format(self.node_url, hash_snapshot_block, self.baking_address)
        _, response = self.wllt_clnt_mngr.send_request(request)

        delegate_staking_balance = 0
        delegators = {}

        try:
            response = parse_json_response(response)
            delegate_staking_balance = int(response["staking_balance"])

            delegators_addresses = response["delegated_contracts"]
            for idx, delegator in enumerate(delegators_addresses):
                request = COMM_DELEGATE_BALANCE.format(self.node_url, hash_snapshot_block, delegator)
                _, response = self.wllt_clnt_mngr.send_request(request)
                response = parse_json_response(response)
                delegators[delegator] = int(response["balance"])

                logger.debug(
                    "Delegator info ({}/{}) fetched: address {}, balance {}".format(idx, len(delegators_addresses),
                                                                                    delegator, delegators[delegator]))
        except:
            logger.warn('No delegators or unexpected error', exc_info=True)

        return delegate_staking_balance, delegators

    def __get_snapshot_block_hash(self, cycle, verbose=False):

        current_level, head_hash, current_cycle = self.__get_current_level(verbose)

        level_for_snapshot_request = (cycle - self.preserved_cycles) * self.blocks_per_cycle + 1

        logger.debug("Current level {}, head hash {}".format(current_level, head_hash))
        logger.debug("Cycle {}, preserved cycles {}, blocks per cycle {}, level of interest {}"
                     .format(cycle, self.preserved_cycles, self.blocks_per_cycle, level_for_snapshot_request))

        block_level = cycle * self.blocks_per_cycle + 1

        if current_level - level_for_snapshot_request >= 0:
            request = COMM_SNAPSHOT.format(self.node_url, block_level, cycle)
            _, response = self.wllt_clnt_mngr.send_request(request)
            snapshots = parse_json_response(response)

            if len(snapshots) == 1:
                chosen_snapshot = snapshots[0]
            else:
                logger.error("Too few or too many possible snapshots found!")
                return ""

            level_snapshot_block = (cycle - self.preserved_cycles - 2) * self.blocks_per_cycle + ( chosen_snapshot + 1) * self.blocks_per_roll_snapshot
            request = COMM_BLOCK.format(self.node_url, head_hash, current_level - level_snapshot_block)
            _, comm_block_response = self.wllt_clnt_mngr.send_request(request)
            comm_block_response = comm_block_response.rstrip()
            comm_block_response_json = extract_json_part(comm_block_response, verbose=True)
            cmd_mngr = CommandManager(verbose=verbose)
            _, hash_snapshot_block = cmd_mngr.execute("echo '{}' | jq -r .hash".format(comm_block_response_json))

            logger.debug("Hash of snapshot block is {}".format(hash_snapshot_block))

            return hash_snapshot_block
        else:
            logger.info("Cycle too far in the future")
            return ""