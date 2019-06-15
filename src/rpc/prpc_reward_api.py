import logging
from time import sleep

import requests

from NetworkConfiguration import init_network_config
from api.reward_api import RewardApi
from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from tzscan.tzscan_mirror_selection_helper import TzScanMirrorSelector
from tzscan.tzscan_reward_api import TzScanRewardApiImpl

logger = main_logger


class PRpcRewardApiImpl(RewardApi):

    COMM_HEAD = "%protocol%://{}/chains/main/blocks/head"
    COMM_DELEGATES = "%protocol%://{}/chains/main/blocks/{}/context/delegates/{}"
    COMM_BLOCK = "%protocol%://{}/chains/main/blocks/{}"
    COMM_SNAPSHOT = COMM_BLOCK + "/context/raw/json/rolls/owner/snapshot/{}/"
    COMM_DELEGATE_BALANCE = "%protocol%://{}/chains/main/blocks/{}/context/contracts/{}"

    def __init__(self, nw, baking_address, node_url, validate=True, verbose=True):
        super(PRpcRewardApiImpl, self).__init__()

        self.blocks_per_cycle = nw['BLOCKS_PER_CYCLE']
        self.preserved_cycles = nw['NB_FREEZE_CYCLE']
        self.blocks_per_roll_snapshot = nw['BLOCKS_PER_ROLL_SNAPSHOT']

        self.baking_address = baking_address
        self.node_url = node_url

        self.verbose = verbose
        self.validate = validate

        # replace protocol placeholder
        protocol = 'https'
        self.COMM_HEAD = self.COMM_HEAD.replace('%protocol%',protocol)
        self.COMM_DELEGATES = self.COMM_DELEGATES.replace('%protocol%',protocol)
        self.COMM_BLOCK = self.COMM_BLOCK.replace('%protocol%',protocol)
        self.COMM_SNAPSHOT = self.COMM_SNAPSHOT.replace('%protocol%',protocol)
        self.COMM_DELEGATE_BALANCE = self.COMM_DELEGATE_BALANCE.replace('%protocol%',protocol)

        if self.validate:
            mirror_selector = TzScanMirrorSelector(nw)
            mirror_selector.initialize()
            self.validate_api = TzScanRewardApiImpl(nw, self.baking_address, mirror_selector)

    def get_nb_delegators(self, cycle, current_level):
        _, delegators = self.__get_delegators_and_delgators_balance(cycle, current_level)
        return len(delegators)

    def get_rewards_for_cycle_map(self, cycle):
        current_level, current_cycle = self.__get_current_level()
        logger.debug("Current level {}, current cycle {}".format(current_level, current_cycle))

        reward_data = {}
        reward_data["delegate_staking_balance"], reward_data["delegators"] = self.__get_delegators_and_delgators_balance(cycle, current_level)
        reward_data["delegators_nb"] = len(reward_data["delegators"])

        # Get last block in cycle where rewards are unfrozen
        level_of_last_block_in_unfreeze_cycle = (cycle+self.preserved_cycles+1) * self.blocks_per_cycle

        logger.debug("Cycle {}, preserved cycles {}, blocks per cycle {}, last_block_cycle {}".format(cycle, self.preserved_cycles, self.blocks_per_cycle, level_of_last_block_in_unfreeze_cycle))

        if current_level - level_of_last_block_in_unfreeze_cycle >= 0:
            unfrozen_rewards = self.__get_unfrozen_rewards(level_of_last_block_in_unfreeze_cycle)
            reward_data["total_rewards"] = unfrozen_rewards

        else:
            logger.warn("Please wait until the rewards and fees for cycle {} are unfrozen".format(cycle))
            reward_data["total_rewards"] = 0

        reward_model = RewardProviderModel(reward_data["delegate_staking_balance"], reward_data["total_rewards"], reward_data["delegators"])

        logger.debug("delegate_staking_balance={}, total_rewards = {}".format(reward_data["delegate_staking_balance"],reward_data["total_rewards"]))
        logger.debug("delegators = {}".format(reward_data["delegators"]))

        if self.validate:
            self.__validate_reward_data(reward_model, cycle)

        return reward_model

    def __get_unfrozen_rewards(self, level_of_last_block_in_unfreeze_cycle):
        request_metadata = self.COMM_BLOCK.format(self.node_url, level_of_last_block_in_unfreeze_cycle) + '/metadata'
        metadata = self.do_rpc_request(request_metadata)
        balance_updates = metadata["balance_updates"]
        unfrozen_rewards = unfrozen_fees = 0

        for i in range(len(balance_updates)):
            balance_update = balance_updates[i]
            if balance_update["kind"] == "freezer":
                if balance_update["delegate"] == self.baking_address:
                    if balance_update["category"] == "rewards":
                        unfrozen_rewards = -int(balance_update["change"])
                        logger.debug("[__get_unfrozen_rewards] Found balance update for reward {}".format(balance_update))
                    elif balance_update["category"] == "fees":
                        unfrozen_fees = -int(balance_update["change"])
                        logger.debug("[__get_unfrozen_rewards] Found balance update for fee {}".format(balance_update))
                    else:
                        logger.debug("[__get_unfrozen_rewards] Found balance update, not including: {}".format(balance_update))

        return unfrozen_fees + unfrozen_rewards

    def do_rpc_request(self, request):
        if self.verbose:
            logger.debug("[do_rpc_request] Requesting URL {}".format(request))

        sleep(0.1) # be nice to public node service

        resp = requests.get(request)
        if resp.status_code != 200:
            raise Exception("Request '{} failed with status code {}".format(request, resp.status_code))

        response = resp.json()
        if self.verbose:
            logger.debug("[do_rpc_request] Response {}".format(response))
        return response

    def __get_current_level(self):
        head = self.do_rpc_request(self.COMM_HEAD.format(self.node_url))
        current_level = int(head["metadata"]["level"]["level"])
        current_cycle = int(head["metadata"]["level"]["cycle"])
        # head_hash = head["hash"]

        return current_level, current_cycle



    def __get_delegators_and_delgators_balance(self, cycle, current_level):

        hash_snapshot_block = self.__get_snapshot_block_hash(cycle, current_level)
        if hash_snapshot_block == "":
            return 0, []

        request = self.COMM_DELEGATES.format(self.node_url, hash_snapshot_block, self.baking_address)

        delegate_staking_balance = 0
        delegators = {}

        try:
            response = self.do_rpc_request(request)
            delegate_staking_balance = int(response["staking_balance"])

            delegators_addresses = response["delegated_contracts"]
            for idx, delegator in enumerate(delegators_addresses):
                request = self.COMM_DELEGATE_BALANCE.format(self.node_url, hash_snapshot_block, delegator)
                response = self.do_rpc_request(request)
                delegators[delegator] = int(response["balance"])

                logger.debug(
                    "Delegator info ({}/{}) fetched: address {}, balance {}".format(idx, len(delegators_addresses),
                                                                                    delegator, delegators[delegator]))
        except:
            logger.warn('No delegators or unexpected error', exc_info=True)

        return delegate_staking_balance, delegators

    def __get_snapshot_block_hash(self, cycle, current_level):

        snapshot_level = (cycle - self.preserved_cycles) * self.blocks_per_cycle + 1
        logger.debug("Reward cycle {}, snapshot level {}".format(cycle,snapshot_level))

        block_level = cycle * self.blocks_per_cycle + 1

        if current_level - snapshot_level >= 0:
            request = self.COMM_SNAPSHOT.format(self.node_url, block_level, cycle)
            snapshots = self.do_rpc_request(request)

            if len(snapshots) == 1:
                chosen_snapshot = snapshots[0]
            else:
                logger.error("Too few or too many possible snapshots found!")
                return ""

            level_snapshot_block = (cycle - self.preserved_cycles - 2) * self.blocks_per_cycle + (chosen_snapshot+1) * self.blocks_per_roll_snapshot
            return level_snapshot_block
            # request = self.COMM_BLOCK.format(self.node_url, level_snapshot_block)
            # response = self.do_rpc_request(request)
            # snapshot = response['hash']
            # logger.debug("Hash of snapshot block is {}".format(snapshot))

            # return snapshot
        else:
            logger.info("Cycle too far in the future")
            return ""


    def __validate_reward_data(self, reward_data_rpc, cycle):
        reward_data_tzscan = self.validate_api.get_rewards_for_cycle_map(cycle)
        if not (reward_data_rpc.delegate_staking_balance == int(reward_data_tzscan.delegate_staking_balance)):
            raise Exception("Delegate staking balance from local node and tzscan are not identical. local node {}, tzscan {}".format(reward_data_rpc.delegate_staking_balance,reward_data_tzscan.delegate_staking_balance ))

        if not (len(reward_data_rpc.delegator_balance_dict) == len(reward_data_tzscan.delegator_balance_dict)):
            raise Exception("Delegators number from local node and tzscan are not identical.")

        if (len(reward_data_rpc.delegator_balance_dict)) == 0:
            return

        if not (reward_data_rpc.delegator_balance_dict == reward_data_tzscan.delegator_balance_dict):
            raise Exception("Delegators' balances from local node and tzscan are not identical.")

        if not reward_data_rpc.total_reward_amount == reward_data_tzscan.total_reward_amount:
            raise Exception("Total rewards from local node and tzscan are not identical.")

        logger.debug("[__validate_reward_data] validation passed")


def test():
    configure_test_logger()

    network_config_map = init_network_config("MAINNET", None, None)
    network_config = network_config_map["MAINNET"]

    prpc = PRpcRewardApiImpl(network_config, "tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj", "mainnet.tezrpc.me",True, True)
    prpc.get_rewards_for_cycle_map(42)


def configure_test_logger():
    test_logger = logging.getLogger('main')
    test_logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(threadName)-9s - %(message)s')
    ch.setFormatter(formatter)
    test_logger.addHandler(ch)
    global logger
    logger = test_logger


if __name__ == '__main__':
    test()