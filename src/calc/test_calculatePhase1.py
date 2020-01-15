from unittest import TestCase

from calc.calculate_phase1 import CalculatePhase1
from model.reward_log import RewardLog


class TestCalculatePhase1(TestCase):
    def test_calculate(self):
        rewards = []
        ratios = [0.25, 0.05, 0.3, 0.15, 0.25]
        total_reward = 1000

        for i, ratio in enumerate(ratios,start=1):
            rl0 = RewardLog(address="addr" + str(i), type="D", staking_balance=total_reward * ratio, current_balance=0)
            rl0.ratio0 = ratio
            rewards.append(rl0)

        excluded_set = {"addr1"}

        phase1 = CalculatePhase1(excluded_set)
        new_rewards, new_total_reward = phase1.calculate(rewards, total_reward)

        self.assertEqual(total_reward * (1 - 0.25), new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        ratio_sum = 0.0

        self.assertTrue(new_rewards)

        # first item is excluded
        # compare rest of the items
        for pr_new, ratio0 in zip(new_rewards[1:], ratios[1:]):
            ratio_sum += pr_new.ratio1

            self.assertAlmostEqual(ratio0 * total_reward, pr_new.ratio1 * new_total_reward, delta=0.000001)

        self.assertEqual(1.0, ratio_sum)
