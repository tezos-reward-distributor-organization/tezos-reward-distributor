from unittest import TestCase

from calc.calculate_phase0 import CalculatePhase0
from model.reward_log import TYPE_OWNERS_PARENT
from api.provider_factory import ProviderFactory

BAKING_ADDRESS = "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V"


class TestCalculatePhase0(TestCase):

    def test_calculate(self):

        nw = {
            'NAME': 'DELPHINET',
            'NB_FREEZE_CYCLE': 3,
            'BLOCK_TIME_IN_SEC': 30,
            'BLOCKS_PER_CYCLE': 2048,
            'BLOCKS_PER_ROLL_SNAPSHOT': 256
        }

        api = ProviderFactory(provider='prpc').newRewardApi(nw, BAKING_ADDRESS, '')

        model = api.get_rewards_for_cycle_map(90)

        phase0 = CalculatePhase0(model)
        reward_data, total_rewards = phase0.calculate()

        delegate_staking_balance = int(model.delegate_staking_balance)

        # total reward ratio is 1
        self.assertEqual(1.0, sum(r.ratio0 for r in reward_data))

        # check that ratio calculations are correct
        delegators_balances_dict = model.delegator_balance_dict

        # check ratios
        for (address, delegator_info), reward in zip(delegators_balances_dict.items(), reward_data):
            # ratio must be equal to stake/total staking balance
            delegator_staking_balance = int(delegator_info["staking_balance"])
            self.assertEqual(delegator_staking_balance / delegate_staking_balance, reward.ratio0)

        # last one is owners record
        self.assertTrue(reward_data[-1].type == TYPE_OWNERS_PARENT)
