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
            self.api = TzKTApi.from_network(nw['NAME'].lower())
        else:
            self.api = TzKTApi.from_url(base_url)
        self.baking_address = baking_address
        self.name = 'tzkt'

    def calc_expected_reward(self, cycle: int, num_blocks: int, num_endorsements: int) -> int:
        """
        Calculate ideal rewards (0 priority, 32 endorsements per block) based on baking rights only
        :param cycle: Cycle
        :param num_blocks: Number of baking rights
        :param num_endorsements: Number of endorsement rights
        """
        proto = self.api.get_protocol_by_cycle(cycle)

        block_reward = \
            proto['constants']['blockReward'][0] \
            * proto['constants']['endorsersPerBlock']

        endorsement_reward = \
            proto['constants']['endorsementReward'][0]

        return num_blocks * block_reward + num_endorsements * endorsement_reward

    def get_rewards_for_cycle_map(self, cycle, expected_reward=False) -> RewardProviderModel:
        """
        Returns reward split in a specified format
        :param cycle:
        :param expected_reward:
        :return: RewardProviderModel(
            delegate_staking_balance=5265698993303,
            total_reward_amount=2790471275,
            delegators_balances={
                'tz1azSbB91MbdcEquhsmJvjVroLs5t4kpdCn': {
                    'staking_balance': 1935059821,
                    'current_balance': 1977503559
                }
            }
        )
        """
        split = self.api.get_reward_split(address=self.baking_address, cycle=cycle, fetch_delegators=True)

        delegate_staking_balance = split['stakingBalance']

        if expected_reward:
            num_blocks = \
                split['ownBlocks'] \
                + split['missedOwnBlocks'] \
                + split['uncoveredOwnBlocks'] \
                + split['futureBlocks']

            num_endorsements = \
                split['endorsements'] \
                + split['missedEndorsements'] \
                + split['uncoveredEndorsements'] \
                + split['futureEndorsements']

            total_reward_amount = self.calc_expected_reward(cycle, num_blocks, num_endorsements)
        else:
            total_reward_amount = \
                split['ownBlockRewards'] \
                + split['extraBlockRewards'] \
                + split['endorsementRewards'] \
                + split['ownBlockFees'] \
                + split['extraBlockFees'] \
                + split['revelationRewards'] \
                + split['doubleBakingRewards'] \
                + split['doubleEndorsingRewards'] \
                - split['doubleBakingLostDeposits'] \
                - split['doubleBakingLostRewards'] \
                - split['doubleBakingLostFees'] \
                - split['doubleEndorsingLostDeposits'] \
                - split['doubleEndorsingLostRewards'] \
                - split['doubleEndorsingLostFees'] \
                - split['revelationLostRewards'] \
                - split['revelationLostFees']

            total_reward_amount = max(0, total_reward_amount)

        delegators_balances = {
            item['address']: {
                'staking_balance': item['balance'],
                'current_balance': item['currentBalance']
            }
            for item in split['delegators']
            if item['balance'] > 0
        }

        # snapshot_level = self.api.get_snapshot_level(cycle)
        # for delegator in self.dexter_contracts_set:
        #    dxtz.process_original_delegators_map(delegators_balances, delegator, snapshot_level)

        return RewardProviderModel(delegate_staking_balance, total_reward_amount, delegators_balances)

    def update_current_balances(self, reward_logs: List[RewardLog]):
        """
        Updates current balance for each iten in list [MODIFIES STATE]
        :param reward_logs: List[RewardLog]
        """
        for rl in reward_logs:
            account = self.api.get_account_by_address(rl.address)
            rl.current_balance = account['balance']
            sleep(self.api.delay_between_calls)
