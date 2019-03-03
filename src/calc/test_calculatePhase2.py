from unittest import TestCase

from calc.calculate_phase2 import CalculatePhase2
from model.reward_log import RewardLog


class TestCalculatePhase2(TestCase):
    def test_calculate(self):
        rewards = []
        ratios = {"addr1": 0.25, "addr2": 0.05, "addr3": 0.3, "addr4": 0.15, "addr5": 0.25}
        total_reward = 1000

        for i, addr in enumerate(ratios, start=1):
            rl0 = RewardLog(address="addr" + str(i), type="D", balance=total_reward * ratios[addr])
            rl0.ratio1 = ratios[addr]
            rewards.append(rl0)

        rewards.append(RewardLog("addrdummy", "D", 0).skip("skipped for testing", 2))

        excluded_set = {"addr1"}

        phase2 = CalculatePhase2(excluded_set)
        new_rewards, new_total_reward = phase2.calculate(rewards, total_reward)

        # new_total_reward = total_reward
        self.assertEqual(total_reward, new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        for pr_new in new_rewards:
            if pr_new.skipped:
                continue
            ratio1 = ratios[pr_new.address]

            # actual and returning ratio1
            self.assertEqual(ratio1, pr_new.ratio1)

            # difference between new amount and old amount is
            # C+C*(a/1-a)-C = C*(a/1-a)
            # -->
            # C'*Total = C *Total + C*(a/1-a)*Total
            self.assertAlmostEqual(ratio1 * total_reward,
                                   pr_new.ratio2 * new_total_reward - ratio1 * (0.25 / 0.75) * new_total_reward,
                                   delta=0.000001)
        ratio_sum = 0.0
        for pr_new in new_rewards:
            if pr_new.ratio2 is None:
                continue
            ratio_sum += pr_new.ratio2

        self.assertEqual(1.0, ratio_sum)
