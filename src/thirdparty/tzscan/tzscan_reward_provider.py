from api.reward_provider_api import RewardProviderApi
from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from thirdparty.tzscan.tzscan_reward_provider_helper import TzScanRewardProviderHelper

class TzScanRewardProvider(RewardProviderApi):
    # reward_data : payment map returned from tzscan
    def __init__(self, nw, baking_address):
        super().__init__()

        self.logger = main_logger
        self.helper = TzScanRewardProviderHelper(nw, baking_address)

    ##
    # return rewards    : tuple (list of PaymentRecord objects, total rewards)
    def provide_for_cycle(self, cycle, verbose=None):
        root = self.helper.get_rewards_for_cycle(cycle, verbose)

        delegate_staking_balance = int(root["delegate_staking_balance"])
        blocks_rewards = int(root["blocks_rewards"])
        future_blocks_rewards = int(root["future_blocks_rewards"])
        endorsements_rewards = int(root["endorsements_rewards"])
        future_endorsements_rewards = int(root["future_endorsements_rewards"])
        fees = int(root["fees"])

        total_reward_amount = (
                    blocks_rewards + endorsements_rewards + future_blocks_rewards + future_endorsements_rewards + fees)

        delegators_balance = root["delegators_balance"]

        delegator_balance_dict = {}
        for dbalance in delegators_balance:
            address = dbalance[0]["tz"]
            balance = int(dbalance[1])

            delegator_balance_dict[address] = balance

        return RewardProviderModel(delegate_staking_balance, total_reward_amount, delegator_balance_dict)
