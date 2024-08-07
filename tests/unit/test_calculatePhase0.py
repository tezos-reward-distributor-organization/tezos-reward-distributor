import vcr
import pytest
from unittest import TestCase
from src.calc.calculate_phase0 import CalculatePhase0
from src.model.reward_log import TYPE_OWNERS_PARENT
from src.api.provider_factory import ProviderFactory
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP, RewardsType

BAKING_ADDRESS = "tz1fikAGfa1MTxX2oJ7UCtvDpVKeH4KTp1UY"
CYCLE = 420
REWARDS_TYPE = RewardsType.ACTUAL


class TestCalculatePhase0(TestCase):
    @vcr.use_cassette(
        "tests/unit/cassettes/test_calculate.yaml",
        filter_headers=["X-API-Key", "authorization"],
        decode_compressed_response=True,
    )
    def test_calculate(self):
        nw = DEFAULT_NETWORK_CONFIG_MAP["MAINNET"]

        api = ProviderFactory(provider="tzkt").newRewardApi(nw, BAKING_ADDRESS, "")

        model = api.get_rewards_for_cycle_map(CYCLE, REWARDS_TYPE)

        phase0 = CalculatePhase0(model)
        reward_data = phase0.calculate()

        own_delegated_balance = int(model.own_delegated_balance)

        # total reward ratio is 1
        self.assertEqual(1.0, sum(r.ratio0 for r in reward_data))

        # check that ratio calculations are correct
        delegators_balances_dict = model.delegator_balance_dict

        # check ratios
        for (address, delegator_info), reward in zip(
            delegators_balances_dict.items(), reward_data
        ):
            # ratio must be equal to stake/total staking balance
            delegated_balance = int(delegator_info["delegated_balance"])
            assert delegated_balance / own_delegated_balance == pytest.approx(
                reward.ratio0, 0.017
            )

        # last one is owners record
        self.assertTrue(reward_data[-1].type == TYPE_OWNERS_PARENT)
