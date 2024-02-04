#  FIXME redo mockups for this test
from unittest.mock import patch, MagicMock
import vcr

from src.pay.batch_payer import BatchPayer, TX_FEES
from src.cli.client_manager import ClientManager
from src.Constants import (
    PUBLIC_NODE_URL,
    RewardsType,
    PRIVATE_SIGNER_URL,
    MUTEZ_PER_TEZ,
)
from src.api.provider_factory import ProviderFactory
from src.config.yaml_baking_conf_parser import BakingYamlConfParser
from src.model.baking_conf import BakingConf
from src.calc.service_fee_calculator import ServiceFeeCalculator
from tests.utils import make_config
from src.model.rules_model import RulesModel
from src.NetworkConfiguration import default_network_config_map
from src.plugins.plugins import PluginManager

from src.calc.phased_payment_calculator import PhasedPaymentCalculator
from src.calc.calculate_phaseMapping import CalculatePhaseMapping
from src.calc.calculate_phaseMerge import CalculatePhaseMerge
from src.calc.calculate_phaseZeroBalance import CalculatePhaseZeroBalance
from src.model.reward_log import TYPE_DELEGATOR

node_endpoint = PUBLIC_NODE_URL["MAINNET"]
network = {"NAME": "MAINNET", "MINIMAL_BLOCK_DELAY": 5}

baking_config = make_config(
    baking_address="tz1NRGxXV9h6SdNaZLcgmjuLx3hyy2f8YoGN",
    payment_address="tz1NRGxXV9h6SdNaZLcgmjuLx3hyy2f8YoGN",
    service_fee=14.99,
    min_delegation_amt=0,
    min_payment_amt=0,
)


PAYOUT_CYCLE = 500
PAYMENT_ADDRESS_BALANCE = int(1000 * MUTEZ_PER_TEZ)
forge = "0" * (TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"])


@patch("src.cli.client_manager.ClientManager.sign", MagicMock(return_value=forge))
@patch(
    "src.rpc.rpc_reward_api.logger",
    MagicMock(debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)),
)
@patch(
    "src.pay.payment_producer.logger",
    MagicMock(debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)),
)
@patch(
    "src.calc.phased_payment_calculator.logger",
    MagicMock(debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)),
)
@patch(
    "src.pay.batch_payer.logger",
    MagicMock(debug=MagicMock(side_effect=print), info=MagicMock(side_effect=print)),
)
@patch(
    "src.pay.batch_payer.BatchPayer.get_payment_address_balance",
    MagicMock(return_value=PAYMENT_ADDRESS_BALANCE),
)
@vcr.use_cassette(
    "tests/regression/cassettes/test_batch_payer_total_payout_amount.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_batch_payer_total_payout_amount():
    # NOTE: For better payment tests we are doing actual tzkz api calls for reward calculation
    factory = ProviderFactory(provider="tzkt")
    parser = BakingYamlConfParser(
        baking_config, None, None, None, None, block_api=factory, api_base_url=None
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
        founders_map=baking_cfg.get_founders_map(),
        owners_map=baking_cfg.get_owners_map(),
        service_fee_calculator=srvc_fee_calc,
        min_delegation_amount=int(
            baking_cfg.get_min_delegation_amount() * MUTEZ_PER_TEZ
        ),
        min_payment_amount=0,
        rules_model=rules_model,
        reward_api=None,
    )

    rewardApi = factory.newRewardApi(
        default_network_config_map["MAINNET"], baking_cfg.get_baking_address(), ""
    )

    # Simulate logic in payment_producer
    reward_logs = []
    attempts = 0
    exiting = False
    while not exiting and attempts < 2:
        attempts += 1

        # Reward data
        # Fetch cycle 51 of granadanet for tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V
        reward_model = rewardApi.get_rewards_for_cycle_map(
            PAYOUT_CYCLE, RewardsType.ACTUAL
        )

        # Calculate rewards - payment_producer.py
        reward_model.computed_reward_amount = reward_model.total_reward_amount
        reward_logs, total_amount = payment_calc.calculate(reward_model)

        # Check total reward amount matches sums of records
        # diff of 1 expected due to floating point arithmetic
        assert (
            total_amount - sum([rl.adjusted_amount for rl in reward_logs if rl.payable])
            <= 1
        )
        exiting = True

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
    reward_logs = [payment_item for payment_item in reward_logs if payment_item.payable]
    reward_logs.sort(key=lambda rl: (rl.type, -rl.staking_balance))

    batch_payer = BatchPayer(
        node_url=node_endpoint,
        pymnt_addr="tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ",
        clnt_mngr=ClientManager(node_endpoint, PRIVATE_SIGNER_URL),
        delegator_pays_ra_fee=True,
        delegator_pays_xfer_fee=True,
        network_config=network,
        plugins_manager=PluginManager(baking_cfg.get_plugins_conf(), dry_run=True),
        dry_run=True,
    )

    # Do the payment
    (
        _,
        _,
        total_payout_amount,
        number_future_payable_cycles,
        exit_code,
    ) = batch_payer.pay(reward_logs, dry_run=True)

    assert exit_code is None

    # Payment does not have status done, paid or injected thus the total payout amount is zero
    assert total_payout_amount == 0, f"total_payout_amount is {total_payout_amount}"
    assert (
        number_future_payable_cycles == 51
    ), f"number_future_payable_cycles is {number_future_payable_cycles}"

    # Check the adjusted amount which is sorted by type and from highest to lowest amount
    expected_amounts_delegates = [
        11452867,
        1291622,
        739251,
        330375,
        81254,
        42527,
        42087,
        40583,
        22541,
        7220,
        4695,
        3384,
        1443,
        1079,
        1015,
        780,
        501,
        398,
        286,
        213,
        203,
        203,
        203,
        95,
        70,
        59,
        43,
        17,
        7,
        3,
        2,
        1,
        0,
        0,
    ]

    for idx, expected_amount in enumerate(expected_amounts_delegates):
        assert reward_logs[idx].type == TYPE_DELEGATOR
        assert reward_logs[idx].adjusted_amount == expected_amount
