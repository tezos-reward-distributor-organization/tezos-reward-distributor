from api.reward_api import RewardApi

from log_config import main_logger
from model.reward_provider_model import RewardProviderModel
from tzstats.tzstats_reward_provider_helper import TzStatsRewardProviderHelper

logger = main_logger
from dexter import dexter_utils as dxtz


class TzStatsRewardApiImpl(RewardApi):

    def __init__(self, nw, baking_address, verbose=False):
        super().__init__()

        self.name = 'tzstats'

        self.verbose = verbose
        self.logger = main_logger
        self.helper = TzStatsRewardProviderHelper(nw, baking_address)

    def get_rewards_for_cycle_map(self, cycle, expected_reward=False):
        root = self.helper.get_rewards_for_cycle(cycle, expected_reward, self.verbose)

        delegate_staking_balance = root["delegate_staking_balance"]
        total_reward_amount = root["total_reward_amount"]
        delegators_balances_dict = root["delegators_balances"]

        snapshot_level = self.helper.get_snapshot_level(cycle)
        for delegator in self.dexter_contracts_set:
            dxtz.process_original_delegators_map(delegators_balances_dict, delegator, snapshot_level)

        return RewardProviderModel(delegate_staking_balance, total_reward_amount, delegators_balances_dict)

    def update_current_balances(self, reward_logs):
        self.helper.update_current_balances(reward_logs)
