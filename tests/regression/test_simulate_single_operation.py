from unittest.mock import patch, MagicMock
from pay.batch_payer import BatchPayer, TZTX_FEE, MUTEZ_PER_GAS_UNIT
from model.reward_log import RewardLog
from cli.client_manager import ClientManager
from http import HTTPStatus
from Constants import CURRENT_TESTNET, PUBLIC_NODE_URL, PaymentStatus

run_ops_parsed = {
    "contents": [
        {
            "metadata": {
                "operation_result": {
                    "status": "applied",
                    "consumed_gas": "100",
                    "paid_storage_size_diff": "24",
                },
                "internal_operation_results": [{"result": {"consumed_gas": "50"}}],
            }
        }
    ]
}


@patch(
    "cli.client_manager.ClientManager.request_url_post",
    MagicMock(return_value=(HTTPStatus.OK, run_ops_parsed)),
)
def test_simulate_single_operation():
    default_fee = TZTX_FEE
    network_config = {"BLOCK_TIME_IN_SEC": 64}
    batch_payer = BatchPayer(
        node_url="node_addr",
        pymnt_addr="tz1234567890123456789012345678901234",
        clnt_mngr=ClientManager(
            node_endpoint=PUBLIC_NODE_URL[CURRENT_TESTNET],
            signer_endpoint="http://127.0.0.1:6732",
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
    assert 150 == consumed_gas
    assert 411 == default_fee + consumed_gas * MUTEZ_PER_GAS_UNIT
    assert int == type(storage)  # type of storage should be int
    assert 24 == storage
