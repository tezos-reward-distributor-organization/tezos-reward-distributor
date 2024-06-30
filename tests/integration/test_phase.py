import logging
import vcr
from time import sleep
from unittest import TestCase
from unittest.mock import patch, MagicMock

from src.Constants import RewardsType, MUTEZ_PER_TEZ
from src.api.provider_factory import ProviderFactory
from src.calc.phased_payment_calculator import PhasedPaymentCalculator
from src.calc.calculate_phaseMapping import CalculatePhaseMapping
from src.calc.calculate_phaseMerge import CalculatePhaseMerge
from src.calc.calculate_phaseZeroBalance import CalculatePhaseZeroBalance
from src.calc.service_fee_calculator import ServiceFeeCalculator
from src.config.yaml_baking_conf_parser import BakingYamlConfParser
from src.exception.api_provider import ApiProviderException
from src.model.rules_model import RulesModel
from src.model.baking_conf import BakingConf
from src.NetworkConfiguration import default_network_config_map
from tests.utils import mock_request_get, make_config, Constants

PAYOUT_CYCLE = 750

logger = logging.getLogger("unittesting")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class TestCalculatePhases(TestCase):
    baking_config = make_config(
        baking_address=Constants.MAINNET_ADDRESS_BAKEXTZ4ME_BAKER,
        payment_address=Constants.MAINNET_ADDRESS_BAKEXTZ4ME_PAYOUT,
        service_fee=10.0,
        min_delegation_amt=0,
        min_payment_amt=0,
    )

    @patch(
        "pay.payment_producer.logger",
        MagicMock(
            debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)
        ),
    )
    @patch(
        "calc.phased_payment_calculator.logger",
        MagicMock(
            debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)
        ),
    )
    @vcr.use_cassette(
        "tests/integration/cassettes/api_consistency/test_process_payouts.yaml",
        filter_headers=["X-API-Key", "authorization"],
        decode_compressed_response=True,
    )
    def test_process_payouts(self):
        logger.debug("")  # Console formatting
        factory = ProviderFactory(provider="prpc")
        parser = BakingYamlConfParser(
            self.baking_config,
            None,
            None,
            None,
            None,
            block_api=factory,
            api_base_url=None,
        )
        parser.parse()
        parser.process()

        cfg_dict = parser.get_conf_obj()
        baking_cfg = BakingConf(cfg_dict)

        srvc_fee_calc = ServiceFeeCalculator(
            baking_cfg.get_full_supporters_set(),
            baking_cfg.get_specials_map(),
            baking_cfg.get_service_fee(),
        )
        rules_model = RulesModel(
            baking_cfg.get_excluded_set_tob(),
            baking_cfg.get_excluded_set_toe(),
            baking_cfg.get_excluded_set_tof(),
            baking_cfg.get_dest_map(),
        )
        rewardApi = factory.newRewardApi(
            default_network_config_map["MAINNET"],
            baking_cfg.get_baking_address(),
            "",
        )
        payment_calc = PhasedPaymentCalculator(
            founders_map=baking_cfg.get_founders_map(),
            owners_map=baking_cfg.get_owners_map(),
            service_fee_calculator=srvc_fee_calc,
            min_delegation_amount=int(
                baking_cfg.get_min_delegation_amount() * MUTEZ_PER_TEZ
            ),
            min_payment_amount=0,
            rules_model=rules_model,
            reward_api=rewardApi,
        )

        # Simulate logic in payment_producer
        reward_logs = []
        attempts = 0
        exiting = False
        while not exiting and attempts < 2:
            attempts += 1
            try:
                # Reward data
                # Fetch cycle 90 of delphinet for tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V
                reward_model = rewardApi.get_rewards_for_cycle_map(
                    PAYOUT_CYCLE, RewardsType.ACTUAL
                )

                # Calculate rewards - payment_producer.py
                reward_model.computed_reward_amount = reward_model.total_reward_amount
                reward_logs, total_amount = payment_calc.calculate(reward_model)

                # Check total reward amount matches sums of records
                self.assertEqual(
                    total_amount, sum([rl.amount for rl in reward_logs if rl.payable])
                )

                exiting = True

            except ApiProviderException as e:
                logger.error(
                    "{:s} error at payment producer loop: '{:s}', will try again.".format(
                        "RPC", str(e)
                    )
                )
                sleep(5)

        #
        # The next 3 phases happen in payment_consumer.py
        #

        # Merge payments to same address
        phaseMerge = CalculatePhaseMerge()
        reward_logs = phaseMerge.calculate(reward_logs)

        # Handle remapping of payment to alternate address
        phaseMapping = CalculatePhaseMapping()
        reward_logs = phaseMapping.calculate(reward_logs, baking_cfg.get_dest_map())

        # Filter zero-balance addresses based on config
        phaseZeroBalance = CalculatePhaseZeroBalance()
        reward_logs = phaseZeroBalance.calculate(
            reward_logs, baking_cfg.get_reactivate_zeroed()
        )

        # Filter out non-payable items
        reward_logs = [pi for pi in reward_logs if pi.payable]
        reward_logs.sort(key=lambda rl: (rl.type, -rl.delegating_balance))

        # Verify that TRD calculated matches known values
        total_amount = 0
        for r in reward_logs:
            assert not r.skipped  # no skips needed
            if r.address == "tz3h7UCrLoFih8nrStVy8GcChtZiVuu1mDYD":
                assert r.amount == 1_632_815
                continue

            assert r.type in "FD"
            assert isinstance(r.paymentaddress, str)
            total_amount += r.amount
        assert total_amount == 22_213_885
