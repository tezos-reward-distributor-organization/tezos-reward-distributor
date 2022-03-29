import logging
from time import sleep
from unittest import TestCase
from unittest.mock import patch, MagicMock

from Constants import CURRENT_TESTNET, RewardsType, MUTEZ_PER_TEZ
from api.provider_factory import ProviderFactory
from calc.phased_payment_calculator import PhasedPaymentCalculator
from calc.calculate_phaseMapping import CalculatePhaseMapping
from calc.calculate_phaseMerge import CalculatePhaseMerge
from calc.calculate_phaseZeroBalance import CalculatePhaseZeroBalance
from calc.service_fee_calculator import ServiceFeeCalculator
from config.yaml_baking_conf_parser import BakingYamlConfParser
from exception.api_provider import ApiProviderException
from functools import cmp_to_key
from model.rules_model import RulesModel
from model.baking_conf import BakingConf
from model.reward_log import cmp_by_type_balance
from NetworkConfiguration import default_network_config_map
from tests.utils import mock_request_get

PAYOUT_CYCLE = 51

logger = logging.getLogger("unittesting")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


class TestCalculatePhases(TestCase):

    baking_config = (
        ""
        "baking_address: tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V\n"
        "delegator_pays_ra_fee: true\n"
        "delegator_pays_xfer_fee: true\n"
        "founders_map:\n"
        "  tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7: 0.25\n"
        "  tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace: 0.75\n"
        "min_delegation_amt: 0.0\n"
        "owners_map:\n"
        "  tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk: 1.0\n"
        "payment_address: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs\n"
        "reactivate_zeroed: true\n"
        "rules_map:\n"
        "  tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs\n"
        "  tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT: TOB\n"
        "  mindelegation: TOB\n"
        "service_fee: 10.0\n"
        "specials_map: {}\n"
        "supporters_set: !!set {}\n"
        "plugins:\n"
        "  enabled:\n"
    )

    @patch("rpc.rpc_reward_api.requests.get", MagicMock(side_effect=mock_request_get))
    @patch(
        "rpc.rpc_reward_api.logger",
        MagicMock(
            debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)
        ),
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
        payment_calc = PhasedPaymentCalculator(
            baking_cfg.get_founders_map(),
            baking_cfg.get_owners_map(),
            srvc_fee_calc,
            int(baking_cfg.get_min_delegation_amount() * MUTEZ_PER_TEZ),
            rules_model,
        )

        rewardApi = factory.newRewardApi(
            default_network_config_map[CURRENT_TESTNET],
            baking_cfg.get_baking_address(),
            "",
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
                self.assertTrue(
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
        reward_logs.sort(key=cmp_to_key(cmp_by_type_balance))

        # TRD Calculated Results
        # tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT type: D, stake bal:   62657.83, cur bal:   62657.83, ratio: 0.327420, fee_ratio: 0.000000, amount:   0.000000, fee_amount: 0.000000, fee_rate: 0.00, payable: N, skipped: Y, at-phase: 1, desc: Excluded by configuration, pay_addr: tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT
        # tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace type: D, stake bal:   55646.70, cur bal:   55646.70, ratio: 0.432340, fee_ratio: 0.000000, amount: 102.988160, fee_amount: 0.000000, fee_rate: 0.00, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace
        # tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ type: D, stake bal:   25689.88, cur bal:   25689.88, ratio: 0.179635, fee_ratio: 0.019959, amount:  42.791010, fee_amount: 4.754557, fee_rate: 0.10, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ
        # tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7 type: D, stake bal:   24916.33, cur bal:   24916.33, ratio: 0.193584, fee_ratio: 0.000000, amount:  46.113902, fee_amount: 0.000000, fee_rate: 0.00, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7
        # tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP type: D, stake bal:    6725.43, cur bal:    6725.43, ratio: 0.047027, fee_ratio: 0.005225, amount:  11.202382, fee_amount: 1.244709, fee_rate: 0.10, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs
        # tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk type: D, stake bal:     981.64, cur bal:     981.64, ratio: 0.007627, fee_ratio: 0.000000, amount:   1.816762, fee_amount: 0.000000, fee_rate: 0.00, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk
        # tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk type: O, stake bal:   14750.53, cur bal:       0.00, ratio: 0.114602, fee_ratio: 0.000000, amount:  27.299548, fee_amount: 0.000000, fee_rate: 0.00, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk
        # tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7 type: F, stake bal:       0.00, cur bal:       0.00, ratio: 0.006296, fee_ratio: 0.000000, amount:   1.499816, fee_amount: 0.000000, fee_rate: 0.00, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7
        # tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace type: F, stake bal:       0.00, cur bal:       0.00, ratio: 0.018889, fee_ratio: 0.000000, amount:   4.499450, fee_amount: 0.000000, fee_rate: 0.00, payable: Y, skipped: N, at-phase: 0, desc: , pay_addr: tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace

        # Final records before creating transactions
        # These values are known to be correct
        cr = {}
        cr["tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ"] = {
            "type": "D",
            "amount": 42791010,
            "pay_addr": "tz1T5woJN3r7SV5v2HGDyA5kurhbD9Y8ZKHZ",
        }
        cr["tz1RRzfechTs3gWdM58y6xLeByta3JWaPqwP"] = {
            "type": "D",
            "amount": 11202382,
            "pay_addr": "tz1RMmSzPSWPSSaKU193Voh4PosWSZx1C7Hs",
        }
        cr["tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace"] = {
            "type": "M",
            "amount": 107487610,
            "pay_addr": "tz1YTMY7Zewx6AMM2h9eCwc8TyXJ5wgn9ace",
        }
        cr["tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7"] = {
            "type": "M",
            "amount": 47613718,
            "pay_addr": "tz1fgX6oRWQb4HYHUT6eRjW8diNFrqjEfgq7",
        }
        cr["tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk"] = {
            "type": "M",
            "amount": 29116310,
            "pay_addr": "tz1L1XQWKxG38wk1Ain1foGaEZj8zeposcbk",
        }

        # Verify that TRD calculated matches known values
        for r in reward_logs:

            # We know this address should be skipped
            if r.address == "tz1V9SpwXaGFiYdDfGJtWjA61EumAH3DwSyT":
                self.assertEqual(r.skipped, 1)
                self.assertEqual(r.amount, 0)
                continue

            # All others we can compare normally
            cmp = cr[r.address]

            self.assertEqual(r.type, cmp["type"])
            self.assertEqual(r.amount, (cmp["amount"]))
            self.assertEqual(r.paymentaddress, cmp["pay_addr"])
