from unittest import TestCase

from calc.calculate_phase0 import CalculatePhase0
from model import reward_log
from api.provider_factory import ProviderFactory

BAKING_ADDRESS = "tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj"


class TestCalculatePhase0(TestCase):

    def test_calculate(self):

        nw = {'NAME': 'MAINNET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 60, 'BLOCKS_PER_CYCLE': 4096,
                'BLOCKS_PER_ROLL_SNAPSHOT': 256}

        api = ProviderFactory(provider='prpc').newRewardApi(nw,  BAKING_ADDRESS, '')
        model = api.get_rewards_for_cycle_map(153)

        phase0 = CalculatePhase0(model)
        reward_data, total_rewards = phase0.calculate()

        staking_balance = int(model.delegate_staking_balance)

        # total reward ratio is 1
        self.assertTrue(1.0, sum(r.ratio0 for r in reward_data))

        # check that ratio calculations are correct
        delegators_balances = model.delegator_balance_dict

        # check ratios
        for (address, balance), reward in zip(delegators_balances.items(),reward_data):
            # ratio must be equal to stake/total staking balance
            self.assertEqual(int(balance) / staking_balance, reward.ratio0)

        # last one is owners record
        self.assertTrue(reward_data[-1].type == reward_log.TYPE_OWNERS_PARENT)
