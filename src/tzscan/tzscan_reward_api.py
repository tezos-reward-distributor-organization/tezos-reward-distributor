from api.reward_api import RewardApi

from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from tzscan.tzscan_reward_provider_helper import TzScanRewardProviderHelper

logger = main_logger


class TzScanRewardApiImpl(RewardApi):

    def __init__(self, nw, baking_address, mirror_selector, verbose=False):
        super().__init__()

        self.verbose = verbose
        self.logger = main_logger
        self.helper = TzScanRewardProviderHelper(nw, baking_address, mirror_selector)

    def get_rewards_for_cycle_map(self, cycle):
        root = self.helper.get_rewards_for_cycle(cycle, self.verbose)

        delegate_staking_balance = int(root["delegate_staking_balance"])
        blocks_rewards = int(root["blocks_rewards"])
        future_blocks_rewards = int(root["future_blocks_rewards"])
        endorsements_rewards = int(root["endorsements_rewards"])
        future_endorsements_rewards = int(root["future_endorsements_rewards"])

        if "lost_rewards_denounciation_baking" in root:
            lost_rewards_denounciation = int(root["lost_rewards_denounciation_baking"])+int(root["lost_rewards_denounciation_endorsement"])
        else:
            lost_rewards_denounciation = int(root["lost_rewards_denounciation"])

        if "lost_fees_denounciation_baking" in root:
            lost_fees_denounciation = int(root["lost_fees_denounciation_baking"])+int(root["lost_fees_denounciation_endorsement"])
        else:
            lost_fees_denounciation = int(root["lost_fees_denounciation"])

        fees = int(root["fees"])

        total_reward_amount = (blocks_rewards + endorsements_rewards + future_blocks_rewards +
                               future_endorsements_rewards + fees - lost_rewards_denounciation - lost_fees_denounciation)

        delegators_balance = root["delegators_balance"]

        delegator_balance_dict = {}
        for dbalance in delegators_balance:
            address = dbalance[0]["tz"]
            balance = int(dbalance[1])

            delegator_balance_dict[address] = balance

        return RewardProviderModel(delegate_staking_balance, total_reward_amount, delegator_balance_dict)
