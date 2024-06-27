import functools

from Constants import MAXIMUM_ROUNDING_ERROR, ALMOST_ZERO
from calc.calculate_phase0 import CalculatePhase0
from calc.calculate_phase1 import CalculatePhase1
from calc.calculate_phase2 import CalculatePhase2
from calc.calculate_phase3 import CalculatePhase3
from calc.calculate_phase4 import CalculatePhase4
from calc.calculate_phase_final import CalculatePhaseFinal
from model.reward_log import (
    TYPE_FOUNDERS_PARENT,
    TYPE_OWNERS_PARENT,
    cmp_by_type_balance,
)
from log_config import main_logger

logger = main_logger.getChild("phased_calculator")


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

    def __init__(
        self,
        founders_map,
        owners_map,
        service_fee_calculator,
        min_delegation_amount,
        min_payment_amount,
        rules_model,
        reward_api,
    ):
        self.rules_model = rules_model
        self.owners_map = owners_map
        self.founders_map = founders_map
        self.fee_calc = service_fee_calculator
        self.min_delegation_amnt = min_delegation_amount
        self.min_payment_amnt = min_payment_amount
        self.reward_api = reward_api

    #
    # calculation details
    #
    # total reward = delegators reward + owners reward = delegators payment + delegators fee + owners payment
    # delegators reward = delegators payment + delegators fee
    # owners reward = owners payment = total reward - delegators reward
    # founders reward = delegators fee = total reward - delegators reward
    ####
    def calculate(self, reward_provider_model, adjustments=None, rerun=False):
        # *************
        # ** phase 0 **
        # *************
        phase0 = CalculatePhase0(reward_provider_model)
        rwrd_logs = phase0.calculate()

        total_rwrd_amnt = int(reward_provider_model.computed_reward_amount)
        if not rerun:
            logger.info(
                "Total rewards before processing is {:<,d} mutez.".format(
                    total_rwrd_amnt
                )
            )
        if total_rwrd_amnt == 0:
            logger.debug("NO REWARDS to process!")
            return [], 0

        assert (
            reward_provider_model.external_delegated_balance
            + reward_provider_model.own_delegated_balance
            == sum([rl.delegating_balance for rl in rwrd_logs])
        )
        assert self.almost_equal(1, sum([rl.ratio for rl in rwrd_logs]))

        # *************
        # ** phase 1 **
        # *************
        phase1 = CalculatePhase1(
            self.rules_model.exclusion_set1, self.min_delegation_amnt
        )
        rwrd_logs, total_rwrd_amnt = phase1.calculate(rwrd_logs, total_rwrd_amnt)

        assert self.almost_equal(
            1, sum([rl.ratio for rl in rwrd_logs if not rl.skipped])
        )

        # *************
        # ** phase 2 **
        # *************
        phase2 = CalculatePhase2(
            self.rules_model.exclusion_set2, self.min_delegation_amnt
        )
        rwrd_logs, total_rwrd_amnt = phase2.calculate(rwrd_logs, total_rwrd_amnt)

        assert self.almost_equal(
            1, sum([rl.ratio for rl in rwrd_logs if not rl.skipped])
        )

        # *************
        # ** phase 3 **
        # *************
        phase3 = CalculatePhase3(
            self.fee_calc, self.rules_model.exclusion_set3, self.min_delegation_amnt
        )
        rwrd_logs, total_rwrd_amnt = phase3.calculate(rwrd_logs, total_rwrd_amnt)

        assert self.almost_equal(
            1, sum([rl.ratio for rl in rwrd_logs if not rl.skipped])
        )

        founder_parent = next(
            filter(lambda x: x.type == TYPE_FOUNDERS_PARENT, rwrd_logs), None
        )

        calculated_founder_rewards = sum(
            [rl.ratio2 for rl in rwrd_logs if rl.skippedatphase == 3]
        ) + sum([rl.service_fee_ratio for rl in rwrd_logs if not rl.skipped])

        if founder_parent:
            assert self.almost_equal(founder_parent.ratio3, calculated_founder_rewards)
        else:
            assert self.almost_equal(0, calculated_founder_rewards)

        owners_parent = next(
            filter(lambda x: x.type == TYPE_OWNERS_PARENT, rwrd_logs), None
        )
        if owners_parent:
            assert owners_parent.service_fee_rate == 0

        # *************
        # ** phase 4 **
        # *************
        phase4 = CalculatePhase4(self.founders_map, self.owners_map, self.reward_api)
        rwrd_logs, total_rwrd_amnt = phase4.calculate(rwrd_logs, total_rwrd_amnt)

        # *****************
        # ** phase final **
        # *****************
        phase_last = CalculatePhaseFinal()
        rwrd_logs, total_rwrd_amnt = phase_last.calculate(
            rwrd_logs, total_rwrd_amnt, adjustments
        )

        # run phases again if calculated minimal payment amount is greater than configured
        if self.min_payment_amnt and self.min_payment_amnt > int(
            min([rl.adjusted_amount for rl in rwrd_logs if not rl.skipped])
        ):
            self.min_delegation_amnt = int(
                min(
                    [
                        rl.delegating_balance
                        for rl in rwrd_logs
                        if not rl.skipped
                        and rl.adjusted_amount > self.min_payment_amnt
                        and rl.delegating_balance
                    ]
                )
            )
            logger.info(
                "Setting min_delegation_amt to {:<,d} mutez due to min_payment_amt set to {:<,d}. Running calculations again.".format(
                    self.min_delegation_amnt, self.min_payment_amnt
                )
            )
            rwrd_logs, total_rwrd_amnt = self.calculate(
                reward_provider_model, adjustments, True
            )
        elif rerun:
            return rwrd_logs, total_rwrd_amnt

        # sort rewards according to type and balance
        rwrd_logs.sort(key=lambda rl: (rl.type, -rl.delegating_balance))

        # check if there is difference between sum of calculated amounts and total_rewards
        total_delegator_amounts = int(
            sum([rl.adjusted_amount for rl in rwrd_logs if not rl.skipped])
        )
        total_adjustments = int(
            sum([rl.adjustment for rl in rwrd_logs if not rl.skipped])
        )
        amnt_pay_diff = int(
            abs(total_rwrd_amnt + total_adjustments - total_delegator_amounts)
        )

        logger.info(
            "Total rewards after processing is {:<,d} mutez.".format(total_rwrd_amnt)
        )

        if total_adjustments < 0:
            logger.info(
                "Total adjustment for past early payout is {:<,d} mutez.".format(
                    total_adjustments
                )
            )
            logger.info(
                "Adjusted total rewards is {:<,d} mutez.".format(
                    total_rwrd_amnt + total_adjustments
                )
            )
        logger.info(
            "Sum of amounts allocated to delegators is {:<,d} mutez".format(
                total_delegator_amounts
            )
        )
        logger.info(
            "Difference between total rewards and sum of amounts allocated to delegators is {:<,d} mutez. "
            "This is due to floating point arithmetic. (max allowed diff is {:<,d} mutez)".format(
                amnt_pay_diff, int(MAXIMUM_ROUNDING_ERROR)
            )
        )

        return rwrd_logs, int(total_rwrd_amnt)

    def almost_equal(self, double1, double2):
        return abs(double1 - double2) < ALMOST_ZERO
