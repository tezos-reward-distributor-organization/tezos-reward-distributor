from _decimal import ROUND_HALF_DOWN
from decimal import Decimal

from calc.calculate_phase_base import CalculatePhaseBase, BY_CONFIGURATION, BY_MIN_DELEGATION
from model.baking_conf import MIN_DELEGATION_KEY


class CalculatePhase1(CalculatePhaseBase):
    """
    -- Phase1 : Total Rewards Phase --

    At phase 1, share of the excluded delegators remains in the staking Balance. Remaining rewards are distributed among other delegators.
    """

    def __init__(self, excluded_set, min_delegation_amount=None) -> None:
        """
        :param excluded_set: set of address to exclude from rewards. Excluded rewards will leave at staking balance. Total reward will be updated.
        """
        super().__init__()

        self.min_delegation_amount = min_delegation_amount
        self.excluded_set = excluded_set
        self.phase = 1

    def calculate(self, reward_data0, total_amount):
        """
        :param reward_data0: reward data from phase 0
        :param total_amount: total amount of rewards.
        :return: tuple (reward_data1,updated_total_amnt)
        reward_data1 is generated by excluding requested addresses. Remaining ratios are adjusted.
        updated_total_amnt is new reward amount where share of excluded addresses are subtracted.
        """

        # rewards, total_amount = self.old_method(reward_data0, total_amount)
        rewards = []
        total_balance_excluded = 0
        total_balance = 0

        # exclude requested addresses from reward list
        for rl0 in reward_data0:
            total_balance += rl0.balance
            if rl0.address in self.excluded_set:
                rl0.skip(desc=BY_CONFIGURATION, phase=self.phase)
                rewards.append(rl0)
                total_balance_excluded += rl0.balance
            elif MIN_DELEGATION_KEY in self.excluded_set and rl0.balance < self.min_delegation_amount:
                rl0.skip(desc=BY_MIN_DELEGATION, phase=self.phase)
                rewards.append(rl0)
                total_balance_excluded += rl0.balance
            else:
                # ratio will be replaced with actual ratio, read below
                rewards.append(rl0)

        new_total_balance = total_balance - total_balance_excluded

        # calculate new ratio using remaining balance
        for rl1 in self.filterskipped(rewards):
            rl1.ratio = rl1.balance / new_total_balance
            rl1.ratio1 = rl1.ratio

        # total reward amount needs to be diminished at the same rate total balance diminishes
        new_total_amnt_multiplier = new_total_balance / total_balance
        new_total_amount = \
            int(Decimal(total_amount * new_total_amnt_multiplier).to_integral_value(rounding=ROUND_HALF_DOWN))

        return rewards, new_total_amount
