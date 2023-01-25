import unittest
from log_config import main_logger
from calc.calculate_phase_base import BY_ZERO_BALANCE
from calc.calculate_phaseZeroBalance import CalculatePhaseZeroBalance
from model import reward_log
from model.reward_log import RewardLog


class TestCalculatePhaseZeroBalance(unittest.TestCase):
    def setUp(self):
        self.logger = main_logger
        self.calculator = CalculatePhaseZeroBalance()
        self.reactivate_zeroed = False
        self.reward_logs = [
            RewardLog(
                address="tz1eyuACLrFdapu9rzjSgrEasTa4sFu1Epnz",
                type=reward_log.TYPE_DELEGATOR,
                staking_balance=5500000,
                current_balance=0,
                originaladdress="tz1eyuACLrFdapu9rzjSgrEasTa4sFu1Epnz",
            ),
            RewardLog(
                address="tz1eyuACLrFdapu9rzjSgrEasTa4sFu1Epn1",
                type=reward_log.TYPE_OWNER,
                staking_balance=5500000,
                current_balance=233,
                originaladdress="tz1eyuACLrFdapu9rzjSgrEasTa4sFu1Epnz",
            ),
        ]

    def test_calculate(self):
        result = self.calculator.calculate(self.reward_logs, self.reactivate_zeroed)
        self.assertEqual(result[0].desc, BY_ZERO_BALANCE)
        self.assertEqual(result[0].skipped, True)
        self.assertEqual(result[0].needs_activation, False)
        self.assertEqual(result[1].desc, "")
        self.assertEqual(result[1].skipped, False)
        self.assertEqual(result[1].needs_activation, False)

    def test_calculate_with_reactivate_zeroed(self):
        self.reactivate_zeroed = True
        result = self.calculator.calculate(self.reward_logs, self.reactivate_zeroed)
        self.assertEqual(result[0].skipped, False)
        self.assertEqual(result[0].needs_activation, True)
        self.assertEqual(result[1].desc, "")
        self.assertEqual(result[1].skipped, False)
        self.assertEqual(result[1].needs_activation, False)
