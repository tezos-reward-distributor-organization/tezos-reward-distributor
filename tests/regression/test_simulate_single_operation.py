from unittest.mock import patch, MagicMock
from pay.batch_payer import BatchPayer, TX_FEES, MUTEZ_PER_GAS_UNIT
from model.reward_log import RewardLog
from cli.client_manager import ClientManager
from http import HTTPStatus
from Constants import (
    CURRENT_TESTNET,
    PUBLIC_NODE_URL,
    PRIVATE_SIGNER_URL,
    PaymentStatus,
)

run_ops_parsed = {
    "contents": [
        {
            "metadata": {
                "operation_result": {
                    "status": "applied",
                    "consumed_milligas": "100000",
                    "paid_storage_size_diff": "24",
                },
                "internal_operation_results": [
                    {"result": {"consumed_milligas": "50000"}}
                ],
            }
        }
    ]
}


@patch(
    "cli.client_manager.ClientManager.request_url_post",
    MagicMock(return_value=(HTTPStatus.OK, run_ops_parsed)),
)
def test_simulate_single_operation():
    default_fee = int(TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"])
    network_config = {"BLOCK_TIME_IN_SEC": 60, "MINIMAL_BLOCK_DELAY": 30}
    batch_payer = BatchPayer(
        node_url="node_addr",
        pymnt_addr="tz1234567890123456789012345678901234",
        clnt_mngr=ClientManager(
            node_endpoint=PUBLIC_NODE_URL[CURRENT_TESTNET],
            signer_endpoint=PRIVATE_SIGNER_URL,
        ),
        delegator_pays_ra_fee=True,
        delegator_pays_xfer_fee=True,
        network_config=network_config,
        plugins_manager=MagicMock(),
        dry_run=False,
    )
    batch_payer.base_counter = 0
    reward_log = RewardLog(
        address="KT1P3Y1mkGASzuJqLh7uGuQEvHatztGuQRgC",
        type="D",
        staking_balance=0,
        current_balance=0,
    )
    reward_log.amount = 15577803
    reward_log.skipped = False
    simulation_status, simulation_results = batch_payer.simulate_single_operation(
        reward_log, reward_log.amount, "hash", "unittest"
    )
    assert PaymentStatus.DONE == simulation_status
    consumed_gas, tx_fee, storage = simulation_results
    assert 250 == consumed_gas
    assert 313.0 == default_fee + consumed_gas * MUTEZ_PER_GAS_UNIT
    assert int == type(storage)  # type of storage should be int
    assert 24 == storage


@patch(
    "cli.client_manager.ClientManager.request_url_post",
    MagicMock(return_value=(HTTPStatus.FORBIDDEN, run_ops_parsed)),
)
def test_failed_simulate_single_operation():
    network_config = {"BLOCK_TIME_IN_SEC": 60, "MINIMAL_BLOCK_DELAY": 30}
    batch_payer = BatchPayer(
        node_url="node_addr",
        pymnt_addr="tz1234567890123456789012345678901234",
        clnt_mngr=ClientManager(
            node_endpoint=PUBLIC_NODE_URL[CURRENT_TESTNET],
            signer_endpoint=PRIVATE_SIGNER_URL,
        ),
        delegator_pays_ra_fee=True,
        delegator_pays_xfer_fee=True,
        network_config=network_config,
        plugins_manager=MagicMock(),
        dry_run=False,
    )
    batch_payer.base_counter = 0
    reward_log = RewardLog(
        address="KT1P3Y1mkGASzuJqLh7uGuQEvHatztGuQRgC",
        type="D",
        staking_balance=0,
        current_balance=0,
    )
    reward_log.amount = 15577803
    reward_log.skipped = False
    simulation_status, simulation_results = batch_payer.simulate_single_operation(
        reward_log, reward_log.amount, "hash", "unittest"
    )
    assert PaymentStatus.FAIL == simulation_status
