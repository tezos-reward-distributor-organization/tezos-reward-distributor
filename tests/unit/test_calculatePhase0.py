from unittest import TestCase
import pytest

from calc.calculate_phase0 import CalculatePhase0
from model.reward_log import TYPE_OWNERS_PARENT
from api.provider_factory import ProviderFactory
from Constants import CURRENT_TESTNET

BAKING_ADDRESS = "tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V"


@pytest.mark.skip
class TestCalculatePhase0(TestCase):

    def test_calculate(self):

        nw = {
            'NAME': CURRENT_TESTNET,
            'NB_FREEZE_CYCLE': 3,
            'BLOCK_TIME_IN_SEC': 30,
            'BLOCKS_PER_CYCLE': 2048,
            'BLOCKS_PER_ROLL_SNAPSHOT': 256,
            'BLOCK_REWARD': 40000000,
            'ENDORSEMENT_REWARD': 1250000
        }

        api = ProviderFactory(provider='prpc').newRewardApi(nw, BAKING_ADDRESS, '')

        model = api.get_rewards_for_cycle_map(11, 'actual')

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
