from pay.utils import (
    calculate_required_fee,
    calculate_tx_fee,
    calculate_consumed_gas,
    calculate_consumed_storage,
    init_payment_logs,
    calculate_estimated_amount_to_pay,
    sort_and_chunk_payment_items,
    caluculate_future_payable_cycles,
)
from Constants import PaymentStatus
import pytest


# @pytest.mark.parametrize(
#     "consumed_gas, size, expected",
#     [
#         (1, 2, 103),
#         (1.4, 1.4444444, 102),
#         (2, 3, 104),
#     ],
# )
# def test_calculate_required_fee(consumed_gas, size, expected):
#     SUT = calculate_required_fee(consumed_gas, size)
#     assert SUT is expected


@pytest.mark.parametrize(
    "fee, expected",
    [
        (1, 10),
        (2.44, 24),
        (3, 30),
    ],
)
def test_calculate_tx_fee(fee, expected):
    SUT = calculate_tx_fee(fee)
    assert SUT is expected


@pytest.mark.parametrize(
    "consumed_gas, size, expected",
    [
        (1, {}, 1),
        (123456, {}, 124),
        (
            123456,
            {"internal_operation_results": [{"result": {"consumed_milligas": 1000}}]},
            125,
        ),
        (
            123456,
            {
                "internal_operation_results": [
                    {"result": {"consumed_milligas": 1000}},
                    {"result": {"consumed_milligas": 1234}},
                ]
            },
            127,
        ),
    ],
)
def test_calculate_consumed_gas(consumed_gas, size, expected):
    SUT = calculate_consumed_gas(consumed_gas, size)
    assert SUT is expected


@pytest.mark.parametrize(
    "metadata, expected",
    [
        ({}, 0),
        ({"operation_result": []}, 0),
        ({"operation_result": {"paid_storage_size_diff": 10}}, 10),
        (
            {
                "operation_result": {"paid_storage_size_diff": 10},
                "internal_operation_results": [
                    {"result": {"paid_storage_size_diff": 10}},
                    {"result": {"paid_storage_size_diff": 10}},
                ],
            },
            30,
        ),
    ],
)
def test_calculate_consumed_storage(metadata, expected):
    SUT = calculate_consumed_storage(metadata)
    assert SUT is expected


# @pytest.mark.parametrize(
#     "payment_items, expected",
#     [
#         ([{"paid2": PaymentStatus.PAID}], []),
#     ],
# )
# def test_init_payment_logs(payment_items, expected):
#     SUT = init_payment_logs(payment_items)
#     assert SUT is expected
