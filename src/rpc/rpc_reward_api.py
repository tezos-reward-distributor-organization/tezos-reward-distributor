from api.reward_api import RewardApi

from log_config import main_logger
from util.rpc_utils import parse_json_response
from tzscan.tzscan_reward_api import TzScanRewardApiImpl

logger = main_logger

COMM_HEAD = " rpc get http://{}/chains/main/blocks/head"
COMM_DELEGATES = " rpc get http://{}/chains/main/blocks/{}/context/delegates/{}"
COMM_BLOCK = " rpc get http://{}/chains/main/blocks/{}~{}/"
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
        if self.validate:
            self.validate_api = TzScanRewardApiImpl(nw, self.baking_address)        


    def get_nb_delegators(self, cycle, verbose=False):
        _, delegators = self.__get_delegators_and_delgators_balance(cycle)
        return len(delegators)


    def get_rewards_for_cycle_map(self, cycle, verbose=False):

        reward_data = {}
        
        reward_data["delegate_staking_balance"], reward_data["delegators"] = self.__get_delegators_and_delgators_balance(cycle)      
        reward_data["delegators_nb"] = len(reward_data["delegators"])
        
        current_level, head_hash = self.__get_current_level(verbose)        

        # Get last block in cycle where rewards are unfrozen
        level_for_relevant_request = (cycle + self.preserved_cycles + 1) * self.blocks_per_cycle

        if current_level - level_for_relevant_request >= 0:
            request_metadata = COMM_BLOCK.format(self.node_url, head_hash, current_level - level_for_relevant_request)+'/metadata/'
            response_metadata = self.wllt_clnt_mngr.send_request(request_metadata)
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
            if self.validate:
                self.__validate_reward_data(reward_data, cycle)
        else:
            logger.warn("Please wait until the rewards and fees for cycle {} are unfrozen".format(cycle))        
            reward_data["total_rewards"] = 0
        
        return reward_data

    def __get_current_level(self, verbose=False):
        response = self.wllt_clnt_mngr.send_request(COMM_HEAD.format(self.node_url))
        head = parse_json_response(response)
        current_level = int(head["metadata"]["level"]["level"])
        head_hash = head["hash"]
        return current_level, head_hash
        
    def __get_delegators_and_delgators_balance(self, cycle, verbose=False):
        
        hash_snapshot_block = self.__get_snapshot_block_hash(cycle)
        if hash_snapshot_block == "":
            return 0, []
            
        request = COMM_DELEGATES.format(self.node_url, hash_snapshot_block, self.baking_address)
        response = self.wllt_clnt_mngr.send_request(request)
        
        delegate_staking_balance = 0
        delegators = {}
        
        try:
            response = parse_json_response(response)
            delegate_staking_balance = int(response["staking_balance"])

            delegators_addresses = response["delegated_contracts"]
            for delegator in delegators_addresses:
                request = COMM_DELEGATE_BALANCE.format(self.node_url, hash_snapshot_block, delegator)
                response = self.wllt_clnt_mngr.send_request(request)
                response = parse_json_response(response)
                delegators[delegator] = int(response["balance"])
        except:
            logger.warn('No delegators or unexpected error')
        
        return delegate_staking_balance, delegators
        
    def __get_snapshot_block_hash(self, cycle, verbose=False):
        
        current_level, head_hash = self.__get_current_level(verbose)
        
        level_for_snapshot_request = (cycle - self.preserved_cycles) * self.blocks_per_cycle + 1    

        if current_level - level_for_snapshot_request >= 0:
            request = COMM_SNAPSHOT.format(self.node_url, head_hash, current_level - level_for_snapshot_request, cycle)
            response = self.wllt_clnt_mngr.send_request(request)
            snapshots = parse_json_response(response)
    
            if len(snapshots) == 1:
                chosen_snapshot = snapshots[0]
            else:
                logger.info("Too few or too many possible snapshots found!")
            
            level_snapshot_block = (cycle - self.preserved_cycles - 2) * self.blocks_per_cycle + ( chosen_snapshot + 1 ) * self.blocks_per_roll_snapshot
            request = COMM_BLOCK.format(self.node_url, head_hash, current_level - level_snapshot_block) + " | jq -r .hash"
            hash_snapshot_block = self.wllt_clnt_mngr.send_request(request).rstrip()
            return hash_snapshot_block
        else:
            logger.info("Cycle too far in the future")
            return ""

    def __validate_reward_data(self, reward_data_rpc, cycle):
        reward_data_tzscan = self.validate_api.get_rewards_for_cycle_map(cycle)
        if not reward_data_rpc["delegate_staking_balance"] == int(reward_data_tzscan["delegate_staking_balance"]):
            raise Exception("Delegate staking balance from local node and tzscan are not identical.")
                
        if not (reward_data_rpc["delegators_nb"]) == (reward_data_tzscan["delegators_nb"]):
            raise Exception("Delegators number from local node and tzscan are not identical.")
        
        if (reward_data_rpc["delegators_nb"]) == 0:
            return
        
        delegators_balance_tzscan = [ int(reward_data_tzscan["delegators_balance"][i][1]) for i in range(len(reward_data_tzscan["delegators_balance"]))]
        print(set(list(reward_data_rpc["delegators"].values())))
        print(set(delegators_balance_tzscan))
        if not set(list(reward_data_rpc["delegators"].values())) == set(delegators_balance_tzscan):
            raise Exception("Delegators' balances from local node and tzscan are not identical.")

        blocks_rewards = int(reward_data_tzscan["blocks_rewards"])
        future_blocks_rewards = int(reward_data_tzscan["future_blocks_rewards"])
        endorsements_rewards = int(reward_data_tzscan["endorsements_rewards"])
        future_endorsements_rewards = int(reward_data_tzscan["future_endorsements_rewards"])
        lost_rewards_denounciation = int(reward_data_tzscan["lost_rewards_denounciation"])
        lost_fees_denounciation = int(reward_data_tzscan["lost_fees_denounciation"])
        fees = int(reward_data_tzscan["fees"])

        total_rewards_tzscan = (blocks_rewards + endorsements_rewards + future_blocks_rewards +
                              future_endorsements_rewards + fees - lost_rewards_denounciation - lost_fees_denounciation)

        if not reward_data_rpc["total_rewards"] == total_rewards_tzscan:
            raise Exception("Total rewards from local node and tzscan are not identical.")
        
