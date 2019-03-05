import functools

from calc.calculate_phase0_tzscan import CalculatePhase0
from calc.calculate_phase1 import CalculatePhase1
from calc.calculate_phase2 import CalculatePhase2
from calc.calculate_phase3 import CalculatePhase3
from calc.calculate_phase4 import CalculatePhase4
from calc.calculate_phase5 import CalculatePhase5
from model.reward_log import cmp


class PahsedPaymentCalculator:
    def __init__(self, founders_map, owners_map, payment_destination_dict, service_fee_calculator, cycle,
                 percent_rounding_mode, payment_rounding_mode, min_delegation_amount):
        self.owners_map = owners_map
        self.founders_map = founders_map
        self.cycle = cycle
        self.fee_calc = service_fee_calculator
        self.prcnt_rm = percent_rounding_mode
        self.pymnt_rm = payment_rounding_mode
        self.pymnt_dest_dict = payment_destination_dict
        self.min_delegation_amnt = min_delegation_amount

    #
    # calculation details
    #
    # total reward = delegators reward + owners reward = delegators payment + delegators fee + owners payment
    # delegators reward = delegators payment + delegators fee
    # owners reward = owners payment = total reward - delegators reward
    # founders reward = delegators fee = total reward - delegators reward
    ####
    def calculate(self, reward_provider_model):
        phase0 = CalculatePhase0(reward_provider_model, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase0.calculate()

        min_delegation_key = "min_delegation"
        phase1_exclude_dest = "tob"
        phase2_exclude_dest = "toe"
        phase3_exclude_dest = "tof"

        min_delegation_dest = phase3_exclude_dest
        if min_delegation_key in self.pymnt_dest_dict:
            min_delegation_dest = self.pymnt_dest_dict[min_delegation_key]

        # prepare phase 1
        excluded_set = set([addr for addr, dest in self.pymnt_dest_dict.items() if dest == phase1_exclude_dest])
        phase_min_delegation_amnt = self.min_delegation_amnt if min_delegation_dest == phase1_exclude_dest else None
        # calculate phase 1
        phase1 = CalculatePhase1(excluded_set, phase_min_delegation_amnt, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase1.calculate(rwrd_logs, total_rwrd_amnt)

        # prepare phase 2
        excluded_set = set([addr for addr, dest in self.pymnt_dest_dict.items() if dest == phase2_exclude_dest])
        phase_min_delegation_amnt = self.min_delegation_amnt if min_delegation_dest == phase2_exclude_dest else None
        # calculate phase 2
        phase2 = CalculatePhase2(excluded_set, phase_min_delegation_amnt, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase2.calculate(rwrd_logs, total_rwrd_amnt)

        # prepare phase 3
        excluded_set = set([addr for addr, dest in self.pymnt_dest_dict.items() if dest == phase3_exclude_dest])
        phase_min_delegation_amnt = self.min_delegation_amnt if min_delegation_dest == phase3_exclude_dest else None
        # calculate phase 3
        phase3 = CalculatePhase3(self.fee_calc,excluded_set, phase_min_delegation_amnt, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase3.calculate(rwrd_logs, total_rwrd_amnt)

        phase4 = CalculatePhase4(self.founders_map,self.owners_map,self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase4.calculate(rwrd_logs, total_rwrd_amnt)

        phase5 = CalculatePhase5()
        rwrd_logs, total_rwrd_amnt = phase5.calculate(rwrd_logs, total_rwrd_amnt)

        rwrd_logs.sort(key=functools.cmp_to_key(cmp))

        return rwrd_logs, total_rwrd_amnt
