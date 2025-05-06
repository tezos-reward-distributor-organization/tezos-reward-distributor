from random import randint
from time import sleep
from log_config import main_logger
import math
from Constants import PaymentStatus


MINIMUM_FEE_MUTEZ = 100
MUTEZ_PER_GAS_UNIT = 0.1
MUTEZ_PER_BYTE = 1
RUNOPS_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%], "signature":"edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"}'
JSON_WRAP = '{"operation": %JSON%,"chain_id":"%chain_id%"}'
MAX_TX_PER_BLOCK_TZ = 200
MAX_TX_PER_BLOCK_KT = 25


def calculate_required_fee(consumed_gas, size):
    return math.ceil(
        MINIMUM_FEE_MUTEZ + MUTEZ_PER_GAS_UNIT * consumed_gas + MUTEZ_PER_BYTE * size
    )


def calculate_tx_fee(default_fee):
    return int(10 * (default_fee))


def build_runops_json_params(branch, content, chain_id):
    runops_json = RUNOPS_JSON.replace("%BRANCH%", branch).replace("%CONTENT%", content)
    return JSON_WRAP.replace("%JSON%", runops_json).replace("%chain_id%", chain_id)


def calculate_consumed_gas(consumed_milligas, metadata):
    consumed_gas = math.ceil(int(consumed_milligas) / 1000)
    if "internal_operation_results" in metadata:
        internal_operation_results = metadata["internal_operation_results"]
        for internal_op in internal_operation_results:
            consumed_gas += math.ceil(
                int(internal_op["result"]["consumed_milligas"]) / 1000
            )
    return consumed_gas


def calculate_consumed_storage(metadata):
    consumed_storage = 0
    if metadata.get("operation_result"):
        if "paid_storage_size_diff" in metadata["operation_result"]:
            consumed_storage += int(
                metadata["operation_result"]["paid_storage_size_diff"]
            )
        if "internal_operation_results" in metadata:
            internal_operation_results = metadata["internal_operation_results"]
            for internal_op in internal_operation_results:
                if "paid_storage_size_diff" in internal_op["result"]:
                    consumed_storage += int(
                        internal_op["result"]["paid_storage_size_diff"]
                    )
        return consumed_storage
    else:
        return consumed_storage


def log_and_fail(operation_result):
    op_error = "Unknown error in simulating contract payout. Payment will be skipped!"
    if (
        "errors" in operation_result
        and len(operation_result["errors"]) > 0
        and "id" in operation_result["errors"][0]
    ):
        op_error = operation_result["errors"][0]["id"]
    main_logger.error(
        "Error while validating operation - Status: {}, Message: {}".format(
            operation_result["status"], op_error
        )
    )
    return PaymentStatus.FAIL, []


def init_payment_logs(payment_items):
    main_logger.info("{} payment items to process".format(len(payment_items)))
    payment_logs_paid = [pi for pi in payment_items if pi.paid.is_paid()]
    if payment_logs_paid:
        main_logger.info(
            "{} payment items are already paid".format(len(payment_logs_paid))
        )

    payment_logs_done = [pi for pi in payment_items if pi.paid.is_done()]
    if payment_logs_done:
        main_logger.info(
            "{} payment items are already processed".format(len(payment_logs_done))
        )

    payment_logs_injected = [pi for pi in payment_items if pi.paid.is_injected()]
    if payment_logs_injected:
        main_logger.info(
            "{} payment items are in injected status".format(len(payment_logs_injected))
        )

    payment_logs = []
    payment_logs.extend(payment_logs_paid)
    payment_logs.extend(payment_logs_done)
    payment_logs.extend(payment_logs_injected)
    for payment_item in payment_logs:
        main_logger.debug(
            "Reward already %s for cycle %s address %s amount %f tz type %s",
            payment_item.paid,
            payment_item.cycle,
            payment_item.address,
            payment_item.adjusted_amount,
            payment_item.type,
        )
    return payment_logs


def calculate_estimated_amount_to_pay(
    payment_items,
    estimated_sum_xfer_fees,
    estimated_sum_burn_fees,
    delegator_pays_xfer_fee,
    delegator_pays_ra_fee,
):
    estimated_amount_to_pay = sum(
        [payment_item.adjusted_amount for payment_item in payment_items]
    )
    if not delegator_pays_xfer_fee:
        estimated_amount_to_pay += estimated_sum_xfer_fees
    if not delegator_pays_ra_fee:
        estimated_amount_to_pay += estimated_sum_burn_fees
    return estimated_amount_to_pay


def sort_and_chunk_payment_items(payment_items):
    payment_items_tz = [
        payment_item
        for payment_item in payment_items
        if payment_item.paymentaddress.startswith("tz")
    ]
    payment_items_KT = [
        payment_item
        for payment_item in payment_items
        if payment_item.paymentaddress.startswith("KT")
    ]
    payment_items_chunks_tz = [
        payment_items_tz[i : i + MAX_TX_PER_BLOCK_TZ]
        for i in range(0, len(payment_items_tz), MAX_TX_PER_BLOCK_TZ)
    ]
    payment_items_chunks_KT = [
        payment_items_KT[i : i + MAX_TX_PER_BLOCK_KT]
        for i in range(0, len(payment_items_KT), MAX_TX_PER_BLOCK_KT)
    ]
    return payment_items_chunks_tz + payment_items_chunks_KT


def calculate_future_payable_cycles(payment_address_balance, estimated_amount_to_pay):
    return int(payment_address_balance // estimated_amount_to_pay - 1)
