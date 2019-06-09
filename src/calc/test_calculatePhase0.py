from unittest import TestCase

from calc.calculate_phase0 import CalculatePhase0
from model import reward_log
from tzscan.tzscan_reward_provider_helper import TzScanRewardProviderHelper


class TestCalculatePhase0(TestCase):

    def test_calculate(self):
        reward_api = TzScanRewardProviderHelper({"NAME": "MAINNET"}, "tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj")
        raw_reward_data = reward_api.get_rewards_for_cycle_map(43)

        phase0 = CalculatePhase0()
        reward_data, total_rewards = phase0.calculate(raw_reward_data)

        staking_balance = int(raw_reward_data['delegate_staking_balance'])

        # total reward ratio is 1
        self.assertTrue(1.0, sum(r.ratio0 for r in reward_data))

        # check that ratio calculations are correct
        delegators_balances = raw_reward_data['delegators_balance']

        # check ratios
        for i in range(len(delegators_balances)):
            delegator_balance = delegators_balances[i]
            delegator_balance_amount = delegator_balance[1]

            # ratio must be equal to stake/total staking balance
            self.assertEqual(int(delegator_balance_amount) / staking_balance, reward_data[i].ratio0)

        # last one is owners record
        self.assertTrue(reward_data[-1].type == reward_log.TYPE_OWNERS_PARENT)
