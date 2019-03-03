from calc.calculate_phase_base import CalculatePhaseBase
from model import reward_log
from model.reward_log import RewardLog
from util.rounding_command import RoundingCommand

MUTEZ = 1e+6


class CalculatePhase0(CalculatePhaseBase):
    """
    Calculate ratios for each delegator based on tz scan data. @see calculate function.
    """

    def __init__(self, prcnt_round_mode=RoundingCommand(None)) -> None:
        """
        Constructor
        :param prcnt_round_mode: RoundingCommand object for percentage calculations. Since this is the first layer in
        calculations RoundingCommand(None) is recommended to avoid rounding.
        """
        super().__init__()

        self.p_rm = prcnt_round_mode

    def calculate(self, tzscan_reward_data, total_amount=0):
        """
        :param tzscan_reward_data: output of TzScanRewardApiImpl
        :param total_amount: 0 value is expected. This value is not used. total amount is obtained from tzscan data.
        :return: tubple (total_reward, reward_data)

        reward_data is a list of RewardLog0 objects. Last item is owners record.
        total_reward is sum( delegator rewards + owner rewards )
        """

        root = tzscan_reward_data

        delegate_staking_balance = int(root["delegate_staking_balance"])
        blocks_rewards = int(root["blocks_rewards"])
        future_blocks_rewards = int(root["future_blocks_rewards"])
        endorsements_rewards = int(root["endorsements_rewards"])
        future_endorsements_rewards = int(root["future_endorsements_rewards"])
        fees = int(root["fees"])

        total_amount = (blocks_rewards + endorsements_rewards + future_blocks_rewards +
                        future_endorsements_rewards + fees) / MUTEZ

        delegators_balance = root["delegators_balance"]

        ratio_sum = 0.0
        total_delegator_balance = 0
        rewards = []

        # calculate how rewards will be distributed
        # ratio is stake/total staking balance
        # total of ratios must be 1
        for dbalance in delegators_balance:
            address = dbalance[0]["tz"]
            balance_in_mutez = int(dbalance[1])
            total_delegator_balance += balance_in_mutez

            ratio = self.p_rm.round(balance_in_mutez / delegate_staking_balance)
            reward_item = RewardLog(address=address, type=reward_log.TYPE_DELEGATOR,
                                    balance=balance_in_mutez)
            reward_item.ratio0 = ratio

            ratio_sum += ratio

            rewards.append(reward_item)

        owners_rl = RewardLog(address=reward_log.TYPE_OWNERS_PARENT, type=reward_log.TYPE_OWNERS_PARENT,
                              balance=delegate_staking_balance - total_delegator_balance)
        owners_rl.ratio0 = (1 - ratio_sum)

        rewards.append(owners_rl)

        return rewards, total_amount
