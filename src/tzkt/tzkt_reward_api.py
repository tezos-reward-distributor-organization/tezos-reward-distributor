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
        :return: RewardProviderModel(
            delegate_staking_balance=5265698993303,
            num_blocks=333,
            num_endorsements=3333,
            delegators_balances={
                'tz1azSbB91MbdcEquhsmJvjVroLs5t4kpdCn': {
                    'staking_balance': 1935059821,
                    'current_balance': 1977503559
                }
            }

        )
        """
        split = self.api.get_reward_split(
            address=self.baking_address, cycle=cycle, fetch_delegators=True
        )

        delegate_staking_balance = split["stakingBalance"]

        # calculate estimated rewards
        num_blocks = (
            split["ownBlocks"]
            + split["missedOwnBlocks"]
            + split["uncoveredOwnBlocks"]
            + split["futureBlocks"]
        )

        num_endorsements = (
            split["endorsements"]
            + split["missedEndorsements"]
            + split["uncoveredEndorsements"]
            + split["futureEndorsements"]
        )

        # rewards earned (excluding equivocation losses)
        rewards_and_fees = (
            split["ownBlockRewards"]
            + split["extraBlockRewards"]
            + split["endorsementRewards"]
            + split["ownBlockFees"]
            + split["extraBlockFees"]
            + split["revelationRewards"]
        )
        denunciation_rewards = (
            split["doubleBakingRewards"] + split["doubleEndorsingRewards"]
        )
        equivocation_losses = (
            split["doubleBakingLostDeposits"]
            + split["doubleBakingLostRewards"]
            + split["doubleBakingLostFees"]
            + split["doubleEndorsingLostDeposits"]
            + split["doubleEndorsingLostRewards"]
            + split["doubleEndorsingLostFees"]
            + split["revelationLostRewards"]
            + split["revelationLostFees"]
        )
        total_reward_amount = max(
            0, rewards_and_fees + denunciation_rewards - equivocation_losses
        )
        # losses due to being offline or not having enough bond
        offline_losses = (
            split["missedOwnBlockRewards"]
            + split["missedExtraBlockRewards"]
            + split["uncoveredOwnBlockRewards"]
            + split["uncoveredExtraBlockRewards"]
            + split["missedEndorsementRewards"]
            + split["uncoveredEndorsementRewards"]
            + split["missedOwnBlockFees"]
            + split["missedExtraBlockFees"]
            + split["uncoveredOwnBlockFees"]
            + split["uncoveredExtraBlockFees"]
        )

        delegators_balances = {
            item["address"]: {
                "staking_balance": item["balance"],
                "current_balance": item["currentBalance"],
            }
            for item in split["delegators"]
            if item["balance"] > 0
        }

        return RewardProviderModel(
            delegate_staking_balance,
            num_blocks,
            num_endorsements,
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
