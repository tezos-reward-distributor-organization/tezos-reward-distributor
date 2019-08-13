from unittest import TestCase

from calc.calculate_phase4 import CalculatePhase4
from model.reward_log import RewardLog, TYPE_FOUNDERS_PARENT, TYPE_OWNER, TYPE_OWNERS_PARENT, TYPE_FOUNDER


class TestCalculatePhase4(TestCase):
    def test_calculate(self):
        rewards = []
        ratios = [0.25, 0.05, 0.3, 0.15, 0.25]
        total_reward = 1000

        for i, ratio in enumerate(ratios, start=1):
            rl0 = RewardLog(address="addr" + str(i), type="D", balance=total_reward * ratio)
            rl0.ratio = ratio
            rl0.ratio3 = ratio
            rewards.append(rl0)

        rewards[0].type = TYPE_OWNERS_PARENT
        rewards[1].type = TYPE_FOUNDERS_PARENT

        rewards.append(RewardLog("addrdummy", "D", 0).skip("skipped for testing", 3))

        founders_map = {"addr1": 0.4, "addr2": 0.6}
        owners_map = {"addr1": 0.6, "addr2": 0.4}

        phase4 = CalculatePhase4(founders_map, owners_map)

        new_rewards, new_total_reward = phase4.calculate(rewards, total_reward)

        # new_total_reward = total_reward
        self.assertEqual(total_reward, new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        ratio_sum = 0.0

        # filter out skipped records
        new_rewards = list(rl for rl in new_rewards if not rl.skipped)

        # 2 owner, 2 founders and 3 delegators
        self.assertEqual(7, len(new_rewards))

        founder_ratio=0.0
        owner_ratio=0.0
        for rl4 in new_rewards:
            if rl4.skipped:
                continue

            if rl4.type == TYPE_FOUNDER:
                founder_ratio += rl4.ratio4
            if rl4.type == TYPE_OWNER:
                owner_ratio += rl4.ratio4

            ratio_sum += rl4.ratio4

        self.assertAlmostEqual(1.0, ratio_sum, delta=1e-6)
        self.assertAlmostEqual(0.25, owner_ratio, delta=1e-6)
        self.assertAlmostEqual(0.05, founder_ratio, delta=1e-6)
