from calc.calculate_phase_base import CalculatePhaseBase, BY_CONFIGURATION, BY_MIN_DELEGATION
from model.baking_conf import MIN_DELEGATION_KEY
from model.reward_log import RewardLog, TYPE_FOUNDERS_PARENT
from util.rounding_command import RoundingCommand

MUTEZ = 1e+6


class CalculatePhase3(CalculatePhaseBase):
    """
    -- Phase3 : Founders Phase --

    At stage 3, Founders record is created. Founders record is later on splitted into founder records, for each founder.
    If any address is excluded at this stage, its reward is given to founders.
    Fee rates are set at this stage.
    """

    def __init__(self, service_fee_calculator, excluded_set, min_delegation_amount=None,
                 prcnt_rm=RoundingCommand(None)) -> None:
        super().__init__()

        self.min_delegation_amount = min_delegation_amount
        self.excluded_set = excluded_set
        self.prcnt_rm = prcnt_rm
        self.fee_calc = service_fee_calculator
        self.phase = 3

    def calculate(self, reward_data2, total_amount):

        rewards = []
        total_excluded_ratio = 0.0

        for rl2 in self.iterateskipped(reward_data2):
            # move skipped records to next phase
            rewards.append(rl2)

        # exclude requested items
        for rl2 in self.filterskipped(reward_data2):
            if rl2.address in self.excluded_set:
                rl2.skip(desc=BY_CONFIGURATION, phase=self.phase)
                rewards.append(rl2)
                total_excluded_ratio += rl2.ratio2
            elif MIN_DELEGATION_KEY in self.excluded_set and rl2.balance < self.min_delegation_amount:
                rl2.skip(desc=BY_MIN_DELEGATION, phase=self.phase)
                rewards.append(rl2)
                total_excluded_ratio += rl2.ratio2
            else:
                rewards.append(rl2)

        total_service_fee_ratio = total_excluded_ratio

        # set fee rates and ratios
        for rl3 in self.filterskipped(rewards):
            service_fee_rate = self.fee_calc.calculate(rl3.address)
            service_fee_ratio = service_fee_rate * rl3.ratio2
            new_ratio = rl3.ratio2 - service_fee_ratio

            total_service_fee_ratio += service_fee_ratio

            rl3.service_fee_rate = service_fee_rate
            rl3.service_fee_ratio = service_fee_ratio
            rl3.ratio3 = new_ratio

        if total_service_fee_ratio > 1e-6:  # >0
            rl3 = RewardLog(address=TYPE_FOUNDERS_PARENT, type=TYPE_FOUNDERS_PARENT, balance=0)
            rl3.ratio3 = total_service_fee_ratio
            rl3.service_fee_ratio = 0
            rl3.service_fee_rate = 0

            rewards.append(rl3)

        return rewards, total_amount
