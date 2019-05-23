import functools

from calc.calculate_phase0_tzscan import CalculatePhase0
from calc.calculate_phase1 import CalculatePhase1
from calc.calculate_phase2 import CalculatePhase2
from calc.calculate_phase3 import CalculatePhase3
from calc.calculate_phase4 import CalculatePhase4
from calc.calculate_phase_final import CalculatePhaseFinal
from model.reward_log import TYPE_FOUNDERS_PARENT, TYPE_OWNERS_PARENT, cmp_by_type_balance
from pay.payment_consumer import logger

MINOR_DIFF = 5
MINOR_RATIO_DIFF = 1e-6


class PhasedPaymentCalculator:
    """
    -- Phase0 : Provider Phase
    -- Phase1 : Total Rewards Phase
    -- Phase2 : Ratios Phase
    -- Phase3 : Founders Phase
    -- Phase4 : Split Phase
    -- Phase5 : Mapping Phase
    -- Phase6 : Merge Phase --
    -- Phase Last : Payment Phase
    """

    def __init__(self, founders_map, owners_map, service_fee_calculator, min_delegation_amount, rules_model):
        self.rules_model = rules_model
        self.owners_map = owners_map
        self.founders_map = founders_map
        self.fee_calc = service_fee_calculator
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
        phase0 = CalculatePhase0(reward_provider_model)
        rwrd_logs, total_rwrd_amnt = phase0.calculate()

        logger.info("Total rewards before processing is {:,} mutez.".format(total_rwrd_amnt))
        if total_rwrd_amnt == 0:
            logger.debug("NO REWARDS to process!")
            return [], 0

        assert reward_provider_model.delegate_staking_balance == sum([rl.balance for rl in rwrd_logs])
        assert self.almost_equal(1, sum([rl.ratio for rl in rwrd_logs]))

        # calculate phase 1
        phase1 = CalculatePhase1(self.rules_model.exclusion_set1, self.min_delegation_amnt)
        rwrd_logs, total_rwrd_amnt = phase1.calculate(rwrd_logs, total_rwrd_amnt)

        assert self.almost_equal(1, sum([rl.ratio for rl in rwrd_logs if not rl.skipped]))

        # calculate phase 2
        phase2 = CalculatePhase2(self.rules_model.exclusion_set2, self.min_delegation_amnt)
        rwrd_logs, total_rwrd_amnt = phase2.calculate(rwrd_logs, total_rwrd_amnt)

        assert self.almost_equal(1, sum([rl.ratio for rl in rwrd_logs if not rl.skipped]))

        # calculate phase 3
        phase3 = CalculatePhase3(self.fee_calc, self.rules_model.exclusion_set3, self.min_delegation_amnt)
        rwrd_logs, total_rwrd_amnt = phase3.calculate(rwrd_logs, total_rwrd_amnt)

        assert self.almost_equal(1, sum([rl.ratio for rl in rwrd_logs if not rl.skipped]))

        founder_parent = next(filter(lambda x: x.type == TYPE_FOUNDERS_PARENT, rwrd_logs), None)

        calculated_founder_rewards = sum([rl.ratio2 for rl in rwrd_logs if rl.skippedatphase == 3]) + sum(
            [rl.service_fee_ratio for rl in rwrd_logs if not rl.skipped])
        assert self.almost_equal(founder_parent.ratio3, calculated_founder_rewards)
        owners_parent = next(filter(lambda x: x.type == TYPE_OWNERS_PARENT, rwrd_logs), None)
        assert owners_parent.service_fee_rate == 0

        phase4 = CalculatePhase4(self.founders_map, self.owners_map)
        rwrd_logs, total_rwrd_amnt = phase4.calculate(rwrd_logs, total_rwrd_amnt)

        # calculate amounts
        phase_last = CalculatePhaseFinal()
        rwrd_logs, total_rwrd_amnt = phase_last.calculate(rwrd_logs, total_rwrd_amnt)

        # sort rewards according to type and balance
        rwrd_logs.sort(key=functools.cmp_to_key(cmp_by_type_balance))

        # check if there is difference between sum of calculated amounts and total_rewards
        total_amount_to_pay = sum([rl.amount for rl in rwrd_logs if not rl.skipped])
        error = abs(total_rwrd_amnt - total_amount_to_pay)

        logger.info("Total rewards after  processing is {:,} mutez.".format(total_rwrd_amnt))

        if error:
            logger.debug("Distributed total amount is {:,} mutez".format(total_amount_to_pay))
            logger.debug("Difference between total rewards and distributed total amount is {} mutez. "
                         "This is due to floating point arithmetic. (max allowed diff is {})"
                         .format(error, MINOR_DIFF))

        assert error <= MINOR_DIFF

        return rwrd_logs, total_rwrd_amnt

    def almost_equal(self, double1, double2):
        return abs(double1 - double2) < MINOR_RATIO_DIFF
