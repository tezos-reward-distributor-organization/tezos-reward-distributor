from unittest import TestCase

from src.calc.calculate_phaseMerge import CalculatePhaseMerge
from src.model.reward_log import RewardLog, TYPE_MERGED, TYPE_DELEGATOR


class TestCalculatePhaseMerge(TestCase):
    def test_merge(self):
        rewards = []

        #
        # Alice is a delegate, owner and founder
        rlAD = RewardLog(
            address="tz1Alice01",
            type="D",
            delegating_balance=10000,
            current_balance=20000,
        )
        rlAD.amount = 1234
        rewards.append(rlAD)

        rlAO = RewardLog(
            address="tz1Alice01", type="O", delegating_balance=10000, current_balance=0
        )
        rlAO.amount = 2345
        rewards.append(rlAO)

        rlAF = RewardLog(
            address="tz1Alice01", type="F", delegating_balance=10000, current_balance=0
        )
        rlAF.amount = 3456
        rewards.append(rlAF)

        #
        # Bob is only a delegate
        rlBD = RewardLog(
            address="tz1Bob01", type="D", delegating_balance=10000, current_balance=0
        )
        rlBD.amount = 5000
        rewards.append(rlBD)

        #
        # Charlie is an Owner and Founder, not a delegate
        rlCO = RewardLog(
            address="tz1Charlie01",
            type="O",
            delegating_balance=10000,
            current_balance=0,
        )
        rlCO.amount = 1122
        rewards.append(rlCO)

        rlCF = RewardLog(
            address="tz1Charlie01",
            type="F",
            delegating_balance=10000,
            current_balance=0,
        )
        rlCF.amount = 2233
        rewards.append(rlCF)

        #
        # Merge Alice and Charlie's payouts
        mergedRewards = CalculatePhaseMerge().calculate(rewards)

        # Check that there now exists only 3 records. Alice's 3 should be merged to 1,
        # and Charlie's 2 merged to 1, Bob only had 1 to begin with
        self.assertEqual(3, len(mergedRewards))

        # Check that Alice's merged record equals the original 3
        aliceSum = 7035
        bobSum = 5000
        charlieSum = 3355

        for r in mergedRewards:
            if r.address == "tz1Alice01":
                self.assertEqual(r.amount, aliceSum)
                self.assertEqual(r.type, TYPE_MERGED)
            elif r.address == "tz1Bob01":
                self.assertEqual(r.amount, bobSum)
                self.assertEqual(r.type, TYPE_DELEGATOR)
            elif r.address == "tz1Charlie01":
                self.assertEqual(r.amount, charlieSum)
                self.assertEqual(r.type, TYPE_MERGED)
