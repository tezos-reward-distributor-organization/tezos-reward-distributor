from calc.calculate_phase_base import (
    CalculatePhaseBase,
    BY_CONFIGURATION,
    BY_MIN_DELEGATION,
)
from model.baking_conf import MIN_DELEGATION_KEY
from model.reward_log import RewardLog, TYPE_FOUNDERS_PARENT
from Constants import ALMOST_ZERO


class CalculatePhase3(CalculatePhaseBase):
    """
    -- Phase3 : Founders Phase --

    At stage 3, Founders record is created. Founders record is later split into founder records, for each founder.
    If any address is excluded at this stage, its reward is given to founders.
    Fee rates are set at this stage.
    """

    def __init__(
        self, service_fee_calculator, excluded_set, min_delegation_amount=None
    ) -> None:
        super().__init__()

        self.min_delegation_amount = min_delegation_amount
        self.excluded_set = excluded_set
        self.fee_calc = service_fee_calculator
        self.phase = 3

    def calculate(self, reward_data2, total_amount):
        new_rewards = []
        total_excluded_ratio = 0.0

        for rl2 in self.iterateskipped(reward_data2):
            # move skipped records to next phase
            new_rewards.append(rl2)

        # exclude requested items
        for rl2 in self.filterskipped(reward_data2):
            if rl2.address in self.excluded_set:
                rl2.skip(desc=BY_CONFIGURATION, phase=self.phase)
                new_rewards.append(rl2)
                total_excluded_ratio += rl2.ratio
            elif (
                MIN_DELEGATION_KEY in self.excluded_set
                and rl2.staking_balance < self.min_delegation_amount
            ):
                rl2.skip(desc=BY_MIN_DELEGATION, phase=self.phase)
                new_rewards.append(rl2)
                total_excluded_ratio += rl2.ratio
            else:
                new_rewards.append(rl2)

        total_service_fee_ratio = total_excluded_ratio

        # set fee rates and ratios
        for rl in self.filterskipped(new_rewards):
            rl.service_fee_rate = self.fee_calc.calculate(rl.originaladdress)
            rl.service_fee_ratio = rl.service_fee_rate * rl.ratio
            rl.ratio = rl.ratio - rl.service_fee_ratio
            rl.ratio3 = rl.ratio

            total_service_fee_ratio += rl.service_fee_ratio

        # create founders parent record
        if total_service_fee_ratio > ALMOST_ZERO:
            rl = RewardLog(
                address=TYPE_FOUNDERS_PARENT,
                type=TYPE_FOUNDERS_PARENT,
                staking_balance=0,
                current_balance=0,
            )
            rl.service_fee_rate = 0
            rl.service_fee_ratio = 0
            rl.ratio = total_service_fee_ratio
            rl.ratio3 = rl.ratio

            new_rewards.append(rl)

        return new_rewards, int(total_amount)
