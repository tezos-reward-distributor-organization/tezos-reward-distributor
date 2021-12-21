from calc.calculate_phase_base import (
    CalculatePhaseBase,
    BY_CONFIGURATION,
    BY_MIN_DELEGATION,
)
from model.baking_conf import MIN_DELEGATION_KEY


class CalculatePhase2(CalculatePhaseBase):
    """
    -- Phase2 : Ratios Phase --

    At phase 2, share of the excluded delegators are distributed among other delegators. Total reward distributed remains the same.
    """

    def __init__(self, excluded_set, min_delegation_amount=None) -> None:
        super().__init__()

        self.min_delegation_amount = min_delegation_amount
        self.excluded_set = excluded_set
        self.phase = 2

    def calculate(self, reward_data1, total_amount):
        """
        :param reward_data1: reward data from phase 1
        :param total_amount: total amount of rewards.
        :return: tuple (reward_data1,total_amount)
        reward_data1 is generated by excluding requested addresses. Remaining ratios are adjusted.
        total_amount is the same as the input total_amount.
        """

        # rewards, total_amount = self.old_method(reward_data0, total_amount)
        rewards = []
        total_balance_excluded = 0
        total_balance = 0

        for rl1 in self.iterateskipped(reward_data1):
            # move skipped records to next phase
            rewards.append(rl1)

        # exclude requested addresses from reward list
        for rl1 in self.filterskipped(reward_data1):

            total_balance += rl1.staking_balance

            if rl1.address in self.excluded_set:
                rl1.skip(desc=BY_CONFIGURATION, phase=self.phase)
                rewards.append(rl1)
                total_balance_excluded += rl1.staking_balance
            elif (
                MIN_DELEGATION_KEY in self.excluded_set
                and rl1.staking_balance < self.min_delegation_amount
            ):
                rl1.skip(desc=BY_MIN_DELEGATION, phase=self.phase)
                rewards.append(rl1)
                total_balance_excluded += rl1.staking_balance
            else:
                # ratio2 will be replaced with actual ratio, read below
                rewards.append(rl1)

        new_total_balance = total_balance - total_balance_excluded

        # calculate new ratio using remaining balance
        for rl2 in self.filterskipped(rewards):
            rl2.ratio = rl2.staking_balance / new_total_balance
            rl2.ratio2 = rl2.ratio

        # total reward amount remains the same
        return rewards, total_amount
