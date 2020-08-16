from unittest import TestCase

from calc.calculate_phase5 import CalculatePhase5
from model.reward_log import RewardLog, TYPE_MERGED


class TestCalculatePhase5(TestCase):
    def test_calculate(self):
        rewards = []
        ratios = [0.25, 0.05, 0.3, 0.15, 0.25]
        total_reward = 1000

        for i, ratio in enumerate(ratios, start=1):
            rl0 = RewardLog(address="addr" + str(i), type="D", staking_balance=total_reward * ratio, current_balance=0)
            rl0.ratio = ratio
            rl0.ratio4 = ratio
            rewards.append(rl0)

        rewards.append(RewardLog("addrdummy", "D", 0, 0).skip("skipped for testing",4))

        phase5 = CalculatePhase5({"addr2":"addr1"})

        new_rewards, new_total_reward = phase5.calculate(rewards, total_reward)

        # filter out skipped records
        new_rewards = list(rl for rl in new_rewards if not rl.skipped)

        # new_total_reward = total_reward
        self.assertEqual(total_reward, new_total_reward)

        # check new ratios sum up to 1
        # old and new reward amount is the same
        ratio_sum = sum(rl.ratio5 for rl in new_rewards)

        # payment address for address2 is address1
        payment_address_set = set(rl.paymentaddress for rl in new_rewards)
        self.assertEqual(4, len(payment_address_set))

        self.assertAlmostEqual(1.0, ratio_sum, delta=1e-6)

        # ratio of records having payment address addr1 must be 0.30 (0.25+0.05)
        self.assertAlmostEqual(0.30,
                               sum(rl.ratio for rl in list(
                                   filter(lambda rl: rl.paymentaddress == "addr1",
                                          filter(lambda rl: not rl.skipped, new_rewards))
                               )),
                               delta=1e-6)
