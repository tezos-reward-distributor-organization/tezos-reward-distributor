from calc.calculate_phase0_tzscan import CalculatePhase0
from calc.calculate_phase1 import CalculatePhase1
from calc.calculate_phase2 import CalculatePhase2
from calc.calculate_phase3 import CalculatePhase3
from calc.calculate_phase4 import CalculatePhase4
from calc.calculate_phase5 import CalculatePhase5
from model.reward_log import TYPE_FOUNDERS_PARENT, TYPE_OWNERS_PARENT


class PahsedPaymentCalculator:
    def __init__(self, founders_map, owners_map, service_fee_calculator, cycle,
                 percent_rounding_mode, payment_rounding_mode, min_delegation_amount, rules_model):
        self.rules_model = rules_model
        self.owners_map = owners_map
        self.founders_map = founders_map
        self.cycle = cycle
        self.fee_calc = service_fee_calculator
        self.prcnt_rm = percent_rounding_mode
        self.pymnt_rm = payment_rounding_mode
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

        assert reward_provider_model.delegate_staking_balance == sum([rl.balance for rl in rwrd_logs])
        assert 1 == sum([rl.ratio0 for rl in rwrd_logs])

        # calculate phase 1
        phase1 = CalculatePhase1(self.rules_model.exclusion_set1, self.min_delegation_amnt, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase1.calculate(rwrd_logs, total_rwrd_amnt)

        assert 1 == sum([rl.ratio1 for rl in rwrd_logs if not rl.skipped])

        # calculate phase 2
        phase2 = CalculatePhase2(self.rules_model.exclusion_set2, self.min_delegation_amnt, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase2.calculate(rwrd_logs, total_rwrd_amnt)

        assert 1 == sum([rl.ratio2 for rl in rwrd_logs if not rl.skipped])

        # calculate phase 3
        phase3 = CalculatePhase3(self.fee_calc, self.rules_model.exclusion_set3, self.min_delegation_amnt,
                                 self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase3.calculate(rwrd_logs, total_rwrd_amnt)

        assert 1 == sum([rl.ratio3 for rl in rwrd_logs if not rl.skipped])
        founder_parent = next(filter(lambda x: x.type == TYPE_FOUNDERS_PARENT, rwrd_logs), None)
        assert founder_parent.ratio3 == sum([rl.ratio2 for rl in rwrd_logs if rl.skippedatphase == 3]) + sum(
            [rl.service_fee_ratio for rl in rwrd_logs if not rl.skipped])
        owners_parent = next(filter(lambda x: x.type == TYPE_OWNERS_PARENT, rwrd_logs), None)
        assert owners_parent.service_fee_rate == 0

        phase4 = CalculatePhase4(self.founders_map, self.owners_map, self.prcnt_rm)
        rwrd_logs, total_rwrd_amnt = phase4.calculate(rwrd_logs, total_rwrd_amnt)

        # prepare phase 5
        phase5 = CalculatePhase5(self.rules_model.dest_map)
        rwrd_logs, total_rwrd_amnt = phase5.calculate(rwrd_logs, total_rwrd_amnt)

        return rwrd_logs, total_rwrd_amnt
