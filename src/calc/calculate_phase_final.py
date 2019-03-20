from calc.calculate_phase_base import CalculatePhaseBase
from model.reward_log import TYPE_FOUNDER, TYPE_OWNER, TYPE_DELEGATOR
from util.rounding_command import RoundingCommand

MUTEZ = 1e+6


class CalculatePhaseFinal(CalculatePhaseBase):
    """
    --Final Stage: Payment Stage--

    At stage final, convert ratios to actual payment amounts.
    """

    def __init__(self, cycle, payment_rounding=RoundingCommand(None)) -> None:
        super().__init__()
        self.cycle = cycle
        self.rm_pymnt = payment_rounding

    def calculate(self, reward_data5, total_amount):
        skipped_rewards = list(self.iterateskipped(reward_data5))
        rewards = list(self.filterskipped(reward_data5))

        # generate new rewards, rewards with the same address are merged
        new_rewards = []
        for rl in rewards:
            rl.amount = int(rl.ratio * total_amount)
            rl.payable = rl.type in [TYPE_FOUNDER, TYPE_OWNER, TYPE_DELEGATOR]
            rl.cycle = self.cycle
            rl.service_fee_amount = self.rm_pymnt.round(rl.service_fee_ratio * total_amount)

            new_rewards.append(rl)

        # add skipped rewards
        new_rewards.extend(skipped_rewards)

        return new_rewards, total_amount
