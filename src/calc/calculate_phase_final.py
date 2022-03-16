from _decimal import ROUND_HALF_DOWN
from decimal import Decimal
from calc.calculate_phase_base import CalculatePhaseBase
from model.reward_log import TYPE_FOUNDER, TYPE_OWNER, TYPE_DELEGATOR


class CalculatePhaseFinal(CalculatePhaseBase):
    """
    --Final Stage: Payment Stage--

    At stage final, convert ratios to actual payment amounts.
    """

    def __init__(self) -> None:
        super().__init__()

    def calculate(self, reward_data5, total_amount, adjustments={}):
        skipped_rewards = list(self.iterateskipped(reward_data5))
        rewards = list(self.filterskipped(reward_data5))

        amount_sum = 0
        last_founder_rl = None
        last_owner_rl = None
        # generate new rewards, rewards with the same address are merged
        new_rewards = []
        for rl in rewards:
            rl.amount = int(
                Decimal(rl.ratio * total_amount).to_integral_value(
                    rounding=ROUND_HALF_DOWN
                )
            )
            if adjustments and rl.address in adjustments.keys():
                rl.adjustment = max(-adjustments[rl.address], -rl.amount)
            else:
                rl.adjustment = 0
            rl.adjusted_amount = int(
                Decimal((rl.ratio * total_amount) + rl.adjustment).to_integral_value(
                    rounding=ROUND_HALF_DOWN
                )
            )
            rl.payable = (
                rl.type in [TYPE_FOUNDER, TYPE_OWNER, TYPE_DELEGATOR]
                and rl.adjusted_amount > 0
            )
            rl.service_fee_amount = int(
                Decimal(rl.service_fee_ratio * total_amount).to_integral_value(
                    rounding=ROUND_HALF_DOWN
                )
            )

            amount_sum += rl.amount
            new_rewards.append(rl)

            # track last owner/founder
            if rl.type == TYPE_FOUNDER:
                last_founder_rl = rl
            if rl.type == TYPE_OWNER:
                last_owner_rl = rl

        # deal with floating point errors
        # error is added/subtracted from last founder or last owner
        amount_diff = total_amount - amount_sum
        if amount_diff:
            if last_founder_rl:
                last_founder_rl.amount += amount_diff
            elif last_owner_rl:
                last_owner_rl.amount += amount_diff

        # add skipped rewards
        new_rewards.extend(skipped_rewards)

        return new_rewards, total_amount
