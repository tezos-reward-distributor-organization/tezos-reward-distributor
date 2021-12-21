from api.reward_api import RewardApi

from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from tzstats.tzstats_reward_provider_helper import TzStatsRewardProviderHelper
from Dexter import dexter_utils as dxtz

logger = main_logger


class TzStatsRewardApiImpl(RewardApi):
    def __init__(self, nw, baking_address):
        super().__init__()
        self.name = "tzstats"
        self.logger = main_logger
        self.helper = TzStatsRewardProviderHelper(nw, baking_address)

    def get_rewards_for_cycle_map(self, cycle, rewards_type):

        root = self.helper.get_rewards_for_cycle(cycle)

        delegate_staking_balance = root["delegate_staking_balance"]
        num_baking_rights = root["num_baking_rights"]
        num_endorsing_rights = root["num_endorsing_rights"]
        delegators_balances_dict = root["delegators_balances"]
        rewards_and_fees = root["rewards_and_fees"]
        equivocation_losses = root["equivocation_losses"]
        denunciation_rewards = root["denunciation_rewards"]
        total_reward_amount = (
            rewards_and_fees - equivocation_losses + denunciation_rewards
        )
        offline_losses = root["offline_losses"]

        snapshot_level = self.helper.get_snapshot_level(cycle)
        for delegator in self.dexter_contracts_set:
            if delegator in delegators_balances_dict:
                dxtz.process_original_delegators_map(
                    delegators_balances_dict, delegator, snapshot_level, self.helper
                )
            else:
                logger.warning(
                    f"The configured Dexter account {delegator} is not delegated to {self.helper.baking_address} "
                    f"at snapshot level {snapshot_level} corresponding to payout cycle {cycle} or has a zero rewards"
                )

        return RewardProviderModel(
            delegate_staking_balance,
            num_baking_rights,
            num_endorsing_rights,
            total_reward_amount,
            rewards_and_fees,
            equivocation_losses,
            denunciation_rewards,
            offline_losses,
            delegators_balances_dict,
            None,
        )

    def update_current_balances(self, reward_logs):
        self.helper.update_current_balances(reward_logs)
