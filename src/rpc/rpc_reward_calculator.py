from api.reward_calculator_api import RewardCalculatorApi

from log_config import main_logger
from util.rounding_command import RoundingCommand
from model.payment_log import PaymentRecord

logger = main_logger

MUTEZ = 1000000

class RpcRewardCalculatorApi(RewardCalculatorApi):

    def __init__(self, founders_map, min_delegation_amt, excluded_set, rc=RoundingCommand(None)):
        super(RpcRewardCalculatorApi, self).__init__(founders_map, excluded_set)
        self.min_delegation_amt_mutez = min_delegation_amt * MUTEZ
        self.logger = main_logger
        self.rc = rc


    def calculate(self, reward_data, verbose=False):
        total_rewards = 0
        rewards = []
        
        delegate_staking_balance, delegators = reward_data["delegate_staking_balance"], reward_data["delegators"]
        
        if len(delegators) > 0:        
            
            total_rewards = reward_data["total_rewards"] / MUTEZ
            
            if total_rewards > 0:        
            
                effective_delegate_staking_balance = delegate_staking_balance
                effective_delegator_addresses = []
        
                # excluded addresses are processed
                for address in delegators:
                    balance = delegators[address]
        
                    if address in self.excluded_set:
                        effective_delegate_staking_balance -= balance
                        continue
                    effective_delegator_addresses.append(address)
        
                
                
                # calculate how rewards will be distributed
                for address in effective_delegator_addresses:
                    balance = delegators[address]
        
                    # Skip those that did not delegate minimum amount
                    if balance < self.min_delegation_amt_mutez:
                        self.logger.debug("Skipping '{}': Low delegation amount ({:.6f})".format(address, (balance / MUTEZ)))
                        continue
        
                    ratio = self.rc.round(balance / effective_delegate_staking_balance)
                    reward = (total_rewards * ratio)
                    
#                    print(address, str(ratio*100) + ' %   -->   ', reward)
                    
                    reward_item = PaymentRecord(address=address, reward=reward, ratio=ratio)
                    
                    rewards.append(reward_item)

        return rewards, total_rewards