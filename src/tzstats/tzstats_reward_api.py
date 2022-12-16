from api.reward_api import RewardApi
import math

from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from tzstats.tzstats_reward_provider_helper import TzStatsRewardProviderHelper
from Constants import MUTEZ_PER_TEZ
from Dexter import dexter_utils as dxtz

logger = main_logger


class TzStatsRewardApiImpl(RewardApi):
    def __init__(self, nw, baking_address):
        super().__init__()
        self.name = "tzstats"
        self.logger = main_logger
        self.helper = TzStatsRewardProviderHelper(nw, baking_address)

        self.blocks_per_cycle = nw["BLOCKS_PER_CYCLE"]
        self.consensus_committee_size = nw["CONSENSUS_COMMITTEE_SIZE"]
        self.endorsing_reward_per_slot = nw["ENDORSING_REWARD_PER_SLOT"]

    def get_rewards_for_cycle_map(self, cycle, rewards_type):

        root = self.helper.get_rewards_for_cycle(cycle)

        delegate_staking_balance = root["delegate_staking_balance"]
        num_baking_rights = root["num_baking_rights"]
        delegators_balances_dict = root["delegators_balances"]
        rewards_and_fees = root["rewards_and_fees"]
        equivocation_losses = root["equivocation_losses"]
        denunciation_rewards = root["denunciation_rewards"]
        total_reward_amount = (
            rewards_and_fees - equivocation_losses + denunciation_rewards
        )
        offline_losses = root["offline_losses"]

        total_active_stake = self.helper.get_cycle_total_stake(cycle)
        number_of_endorsements_per_cycle = (
            self.blocks_per_cycle * self.consensus_committee_size
        )

        # https://tezos-dev.slack.com/archives/CV5NX7F2L/p1649433246273169?thread_ts=1648854391.875409&cid=CV5NX7F2L
        potential_endorsement_rewards = int(
            math.floor(
                delegate_staking_balance
                * number_of_endorsements_per_cycle
                / total_active_stake
            )
            * self.endorsing_reward_per_slot
            / MUTEZ_PER_TEZ
        )

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
            potential_endorsement_rewards,
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
