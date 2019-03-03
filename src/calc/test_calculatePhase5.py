from unittest import TestCase

from calc.calculate_phase4 import CalculatePhase4
from calc.calculate_phase5 import CalculatePhase5
from calc.service_fee_calculator import ServiceFeeCalculator
from model.reward_log import RewardLog, TYPE_FOUNDERS_PARENT, TYPE_OWNER, TYPE_OWNERS_PARENT, TYPE_FOUNDER, TYPE_MERGED


class TestCalculatePhase5(TestCase):
    def test_calculate(self):
        rewards = []
        ratios = [0.25, 0.05, 0.3, 0.15, 0.25]
        total_reward = 1000

        for i, ratio in enumerate(ratios, start=1):
            rl0 = RewardLog(address="addr" + str(i), type="D", balance=total_reward * ratio)
            rl0.ratio4 = ratio
            rewards.append(rl0)

        rewards[0].address = "addr1"
        rewards[1].address = "addr1"

        rewards.append(RewardLog("addrdummy","D",0).skip("skipped for testing",4))

        phase5 = CalculatePhase5()

        new_rewards, new_total_reward = phase5.calculate(rewards, total_reward)

        # filter out skipped records
        new_rewards = list(rl for rl in new_rewards if not rl.skipped)

        # new_total_reward = total_reward
        self.assertEqual(total_reward, new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        ratio_sum = sum(rl.ratio5 for rl in new_rewards)

        # 2 records are merged
        self.assertEqual(4, len(new_rewards))

        self.assertAlmostEqual(1.0, ratio_sum, delta=1e-6)

        # ratio of merged record must be 0.30 (0.25+0.05)
        self.assertAlmostEqual(0.30,
                               list(
                                   filter(lambda rl: rl.type == TYPE_MERGED,
                                          filter(lambda rl: not rl.skipped, new_rewards))
                               )[0].ratio5,
                               delta=1e-6)
