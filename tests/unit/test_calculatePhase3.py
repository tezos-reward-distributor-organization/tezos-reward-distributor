from unittest import TestCase

from calc.calculate_phase3 import CalculatePhase3
from calc.service_fee_calculator import ServiceFeeCalculator
from model.reward_log import RewardLog, TYPE_FOUNDERS_PARENT
from Constants import ALMOST_ZERO


class TestCalculatePhase3(TestCase):
    def test_calculate(self):
        rewards = []
        ratios = [0.25, 0.05, 0.3, 0.15, 0.25]
        total_reward = 1000

        for i, ratio in enumerate(ratios, start=1):
            rl0 = RewardLog(
                address="addr" + str(i),
                type="D",
                staking_balance=total_reward * ratio,
                current_balance=0,
            )
            rl0.ratio = ratio
            rl0.ratio2 = ratio
            rewards.append(rl0)

        rewards.append(RewardLog("addrdummy", "D", 0, 0).skip("skipped for testing", 2))

        excluded_set = {"addr1"}

        fee_calculator = ServiceFeeCalculator(set(), dict(), 20)  # 20% fee
        phase3 = CalculatePhase3(fee_calculator, excluded_set)

        new_rewards, new_total_reward = phase3.calculate(rewards, total_reward)

        # filter out skipped records
        new_rewards = list(rl for rl in new_rewards if not rl.skipped)

        # new_total_reward = total_reward
        self.assertEqual(total_reward, new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        ratio_sum = 0.0
        service_fee_ratio_sum = 0.0

        founder_pl = None
        for rl3 in new_rewards:
            if rl3.skipped:
                continue

            if rl3.type == TYPE_FOUNDERS_PARENT:
                founder_pl = rl3

            ratio_sum += rl3.ratio3
            service_fee_ratio_sum += rl3.service_fee_ratio

        self.assertAlmostEqual(1.0, ratio_sum, delta=ALMOST_ZERO)
        self.assertAlmostEqual(0.15, service_fee_ratio_sum, delta=ALMOST_ZERO)
        self.assertAlmostEqual(0.4, founder_pl.ratio3, delta=ALMOST_ZERO)

    def test_calculate_sepecials(self):
        rewards = []
        ratios = [0.25, 0.05, 0.3, 0.15, 0.25]
        total_reward = 1000

        for i, ratio in enumerate(ratios, start=1):
            rl0 = RewardLog(
                address="addr" + str(i),
                type="D",
                staking_balance=total_reward * ratio,
                current_balance=0,
            )
            rl0.ratio = ratio
            rl0.ratio2 = ratio
            rewards.append(rl0)

        rewards.append(RewardLog("addrdummy", "D", 0, 0).skip("skipped for testing", 2))

        excluded_set = {"addr1"}
        supporters_set = {"addr2"}
        specials_map = {"addr3": 30}

        fee_calculator = ServiceFeeCalculator(
            supporters_set, specials_map, 20
        )  # 20% fee
        phase3 = CalculatePhase3(fee_calculator, excluded_set)

        new_rewards, new_total_reward = phase3.calculate(rewards, total_reward)

        # filter out skipped records
        new_rewards = list(rl for rl in new_rewards if not rl.skipped)

        # new_total_reward = total_reward
        self.assertEqual(total_reward, new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        ratio_sum = 0.0
        service_fee_ratio_sum = 0.0

        founder_pl = None
        for rl3 in new_rewards:
            if rl3.skipped:
                continue

            if rl3.type == TYPE_FOUNDERS_PARENT:
                founder_pl = rl3

            ratio_sum += rl3.ratio3
            service_fee_ratio_sum += rl3.service_fee_ratio

        self.assertAlmostEqual(1.0, ratio_sum, delta=ALMOST_ZERO)
        self.assertAlmostEqual(0.17, service_fee_ratio_sum, delta=ALMOST_ZERO)
        self.assertAlmostEqual(0.42, founder_pl.ratio3, delta=ALMOST_ZERO)

        for rl3 in new_rewards:
            if rl3.skipped:
                continue

            if rl3.address == "addr2":
                self.assertEqual(0, rl3.service_fee_rate)
                self.assertEqual(0, rl3.service_fee_ratio)

            if rl3.address == "addr3":
                self.assertEqual(0.3, rl3.service_fee_rate)
                self.assertEqual(
                    specials_map["addr3"] / 100 * rl3.ratio2, rl3.service_fee_ratio
                )
