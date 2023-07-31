from unittest.mock import patch, MagicMock
from pay.batch_payer import BatchPayer, TX_FEES, OpCounter
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
                    {"result": {"consumed_milligas": "40000"}}
                ],
            }
        }
    ]
}

forge = "0" * (TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"])

payment_head = {
    "hash": "BLyUNtn24LzUDyAgfPmvoJ3Lmqfcqw7tKdEX9thmXD62P8kgpyt",
    "chain_id": "NetXZSsxBpMQeAT",
    "metadata": {"protocol": "PtHangz2aRngywmSRGGvrcTyMbbdpWdpFKuS4uMWxg2RaH9i1qx"},
}

TEST_TZ_ADDRESS = "tz2JrnsSXPkN3QHKsYm1bGijwVHc1vFaR5kU"


@patch(
    "cli.client_manager.ClientManager.request_url_post",
    side_effect=[
        (HTTPStatus.OK, run_ops_parsed),
        (HTTPStatus.OK, forge),
        (HTTPStatus.OK, forge),
        (HTTPStatus.OK, None),
    ],
)
@patch(
    "cli.client_manager.ClientManager.request_url",
    side_effect=[
        (HTTPStatus.OK, 3209357),
        (HTTPStatus.OK, payment_head),
    ],
)
@patch(
    "cli.client_manager.ClientManager.sign",
    return_value=forge,
)
def test_attempt_single_batch_tz(sign, request_url, request_url_post):
    network_config = {"BLOCK_TIME_IN_SEC": 60, "MINIMAL_BLOCK_DELAY": 30}
    batch_payer = BatchPayer(
        node_url="node_addr",
        pymnt_addr=TEST_TZ_ADDRESS,
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
        address=TEST_TZ_ADDRESS,
        type="D",
        staking_balance=80,
        current_balance=100,
    )

    reward_log.adjusted_amount = 15577803
    reward_log.skipped = False

    opt_counter = OpCounter()
    status, operation_hash, _ = batch_payer.attempt_single_batch(
        [reward_log], opt_counter, dry_run=True
    )
    assert status == PaymentStatus.DONE
    assert operation_hash is None
    assert reward_log.delegator_transaction_fee == int(
        TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"]
    )
    assert opt_counter.counter == 3209358


TEST_KT_ADDRESS = "KT1SZrurTqTBWsWsZUVR27GZ8bHK3EhFV62g"


@patch(
    "cli.client_manager.ClientManager.request_url_post",
    side_effect=[
        (HTTPStatus.OK, run_ops_parsed),
        (HTTPStatus.OK, forge),
        (HTTPStatus.OK, run_ops_parsed),
        (HTTPStatus.OK, forge),
        (HTTPStatus.OK, forge),
    ],
)
@patch(
    "cli.client_manager.ClientManager.request_url",
    side_effect=[
        (HTTPStatus.OK, 3),
        (HTTPStatus.OK, payment_head),
    ],
)
@patch(
    "cli.client_manager.ClientManager.sign",
    return_value=forge,
)
def test_attempt_single_batch_KT(sign, request_url, request_url_post):
    network_config = {"BLOCK_TIME_IN_SEC": 60, "MINIMAL_BLOCK_DELAY": 30}
    batch_payer = BatchPayer(
        node_url="node_addr",
        pymnt_addr=TEST_TZ_ADDRESS,
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
        address=TEST_KT_ADDRESS,
        type="D",
        staking_balance=50,
        current_balance=100,
    )

    reward_log.adjusted_amount = 15577803
    reward_log.skipped = False

    opt_counter = OpCounter()
    status, operation_hash, _ = batch_payer.attempt_single_batch(
        [reward_log], opt_counter, dry_run=True
    )
    assert status == PaymentStatus.DONE
    assert operation_hash is None
    assert reward_log.delegator_transaction_fee == 9004
    assert opt_counter.counter == 4
