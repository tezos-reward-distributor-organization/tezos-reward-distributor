from typing import List
from time import sleep

from api.reward_api import RewardApi
from model.reward_provider_model import RewardProviderModel
from model.reward_log import RewardLog
from tzkt.tzkt_api import TzKTApi


class TzKTRewardApiImpl(RewardApi):
    def __init__(self, nw, baking_address, base_url=None):
        super(TzKTRewardApiImpl, self).__init__()
        if base_url is None:
            self.api = TzKTApi.from_network(nw["NAME"])
        else:
            self.api = TzKTApi.from_url(base_url)
        self.baking_address = baking_address
        self.name = "tzkt"

    def get_rewards_for_cycle_map(self, cycle, rewards_type) -> RewardProviderModel:
        """
        Returns reward split in a specified format
        :param cycle:
        :rtype: RewardProviderModel
        """
        split = self.api.get_reward_split(
            address=self.baking_address, cycle=cycle, fetch_delegators=True
        )

        own_delegated_balance = split["ownDelegatedBalance"]
        external_delegated_balance = split["externalDelegatedBalance"]

        # calculate estimated rewards
        num_blocks = split["blocks"] + split["missedBlocks"] + split["futureBlocks"]

        # warning: futureEndorsementRewards will be 0 after the cycle ran.
        # if we query a past cycle then we set the potential_endorsement_rewards with the
        # actual endorsement reward for consistency with other reward apis
        # But after cycle ran, we never pay estimates, so this value will not be used.
        potential_endorsement_rewards = (
            split["futureEndorsementRewards"]
            if self.api.get_current_cycle() <= cycle
            else split["endorsementRewards"]
        )

        # rewards earned (excluding equivocation losses)
        rewards_and_fees = (
            split["blockRewardsDelegated"]
            + split["endorsementRewardsDelegated"]
            + split["nonceRevelationRewardsDelegated"]
            + split["vdfRevelationRewardsDelegated"]
        )
        denunciation_rewards = (
            split["doubleBakingRewards"]
            + split["doubleEndorsingRewards"]
            + split["doublePreendorsingRewards"]
        )
        equivocation_losses = (
            split["doubleBakingLostUnstaked"]
            + split["doubleEndorsingLostUnstaked"]
            + split["doublePreendorsingLostUnstaked"]
        )
        total_reward_amount = max(
            0, rewards_and_fees + denunciation_rewards - equivocation_losses
        )
        # losses due to being offline or not having enough bond
        offline_losses = (
            split["missedBlockRewards"]
            + split["missedBlockFees"]
            + split["missedEndorsementRewards"]
        )

        delegators_balances = {
            item["address"]: {
                "delegated_balance": item["delegatedBalance"],
                # FIXME: current_balance is deprecated and no longer accurate
                # Instead, tzkt provides a boolean "empty" that can be used.
                "current_balance": item["currentDelegatedBalance"],
            }
            for item in split["delegators"]
            if item["balance"] > 0
        }

        return RewardProviderModel(
            own_delegated_balance,
            external_delegated_balance,
            num_blocks,
            potential_endorsement_rewards,
            total_reward_amount,
            rewards_and_fees,
            equivocation_losses,
            denunciation_rewards,
            offline_losses,
            delegators_balances,
            None,
        )

    def update_current_balances(self, reward_logs: List[RewardLog]):
        """
        Updates current balance for each iten in list [MODIFIES STATE]
        :param reward_logs: List[RewardLog]
        """
        for rl in reward_logs:
            account = self.api.get_account_by_address(rl.address)
            rl.current_balance = account["balance"]
            sleep(self.api.delay_between_calls)
