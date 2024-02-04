import os
import queue
import shutil
from http import HTTPStatus
from distutils.dir_util import copy_tree
from unittest import TestCase
from unittest.mock import patch, MagicMock
from src.Constants import PaymentStatus, RewardsType, TEMP_TEST_DATA_DIR
from src.cli.client_manager import ClientManager
from src.pay.payment_consumer import PaymentConsumer
from src.pay.payment_producer_abc import PaymentProducerABC
from src.pay.retry_producer import RetryProducer
from src.util.csv_payment_file_parser import CsvPaymentFileParser
from src.util.dir_utils import get_payment_report_file_path


TEST_REPORT_DIR = "tests/integration/test_reports"
TEST_REPORT_TEMP_DIR = os.path.join(
    "tests", os.path.normpath(TEMP_TEST_DATA_DIR), "test_reports_temp"
)


def request_url(url, timeout=None):
    print(url)
    if "/chains/main/blocks/head/context/contracts/" in url:
        return HTTPStatus.OK, 1
    if url == "/chains/main/blocks/head~10":
        return HTTPStatus.OK, dict(
            {
                "header": dict({"level": 1000}),
                "hash": "hash",
                "chain_id": "unittest",
                "metadata": dict({"protocol": "protocol1"}),
            }
        )
    if url == "/chains/main/blocks/head":
        return HTTPStatus.OK, dict(
            {
                "header": dict({"level": 1000}),
                "hash": "hash",
                "chain_id": "unittest",
                "metadata": dict({"protocol": "protocol1"}),
            }
        )
    if url == "/chains/main/blocks/head/operation_hashes":
        return HTTPStatus.OK, ["xxx_op_hash"]

    return HTTPStatus.NOT_FOUND, "aaaaa" + str(timeout)


def request_url_post(cmd, json_params, timeout=None):
    print(cmd)
    if cmd == "/chains/main/blocks/head/helpers/scripts/run_operation":
        return HTTPStatus.OK, dict(
            {
                "contents": [
                    dict(
                        {
                            "metadata": dict(
                                {"operation_result": dict({"status": "done"})}
                            )
                        }
                    )
                ]
            }
        )
    if cmd == "/chains/main/blocks/head/helpers/forge/operations":
        return HTTPStatus.OK, "bytes"
    if cmd == "/chains/main/blocks/head/helpers/preapply/operations":
        return HTTPStatus.OK, "xxxx"
    if cmd == "/injection/operation":
        return HTTPStatus.OK, "xxx_op_hash"

    return HTTPStatus.NOT_FOUND, "bbbb" + str(json_params) + str(timeout)


class TestRetryProducerBeforeInitialCycle(TestCase):
    def setUp(self):
        try:
            copy_tree(TEST_REPORT_DIR, TEST_REPORT_TEMP_DIR)
            if not os.path.exists(os.path.join(TEST_REPORT_TEMP_DIR, "done")):
                os.makedirs(os.path.join(TEST_REPORT_TEMP_DIR, "done"))
        except OSError:
            pass

    @patch(
        "src.pay.payment_consumer.BatchPayer.get_payment_address_balance",
        MagicMock(return_value=100_000_000),
    )
    @patch(
        "src.pay.payment_consumer.BatchPayer.simulate_single_operation",
        MagicMock(return_value=(PaymentStatus.DONE, (500, 100, 0))),
    )
    @patch("src.pay.batch_payer.sleep", MagicMock())
    @patch(
        "src.cli.client_manager.ClientManager.request_url",
        MagicMock(side_effect=request_url),
    )
    @patch(
        "src.cli.client_manager.ClientManager.request_url_post",
        MagicMock(side_effect=request_url_post),
    )
    @patch(
        "src.cli.client_manager.ClientManager.sign",
        MagicMock(
            return_value="edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"
        ),
    )
    def test_retry_failed_payments_before_initial_cycle(self):
        """This is a test about retrying failed operations in a cycle
        before initial_cycle passed at parameter.
        Input is a past payment report with failures at cycle 10.
        Initial cycle is set to 11.
        It should NOT trigger any payment.
        """
        payment_queue = queue.Queue(100)

        retry_producer = RetryProducer(
            payment_queue,
            _DummyRpcRewardApi(),
            _TestPaymentProducer(),
            TEST_REPORT_TEMP_DIR,
            11,
        )
        retry_producer.retry_failed_payments()

        self.assertEqual(0, len(payment_queue.queue))


class TestRetryProducer(TestCase):
    def setUp(self):
        try:
            copy_tree(TEST_REPORT_DIR, TEST_REPORT_TEMP_DIR)
            if not os.path.exists(os.path.join(TEST_REPORT_TEMP_DIR, "done")):
                os.makedirs(os.path.join(TEST_REPORT_TEMP_DIR, "done"))
        except OSError:
            pass

    @patch(
        "src.pay.payment_consumer.BatchPayer.get_payment_address_balance",
        MagicMock(return_value=100_000_000),
    )
    @patch(
        "src.pay.payment_consumer.BatchPayer.simulate_single_operation",
        MagicMock(return_value=(PaymentStatus.DONE, (500, 100, 0))),
    )
    @patch("src.pay.batch_payer.sleep", MagicMock())
    @patch(
        "src.cli.client_manager.ClientManager.request_url",
        MagicMock(side_effect=request_url),
    )
    @patch(
        "src.cli.client_manager.ClientManager.request_url_post",
        MagicMock(side_effect=request_url_post),
    )
    @patch(
        "src.cli.client_manager.ClientManager.sign",
        MagicMock(
            return_value="edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"
        ),
    )
    def test_retry_failed_payments(self):
        """This is a test about retrying failed operations.
        Input is a past payment report which contains 31 payment items,
        26 of them were successful and 5 of them were failed. The final report
        should report 31 successful transactions.
        """
        payment_queue = queue.Queue(100)

        retry_producer = RetryProducer(
            payment_queue,
            _DummyRpcRewardApi(),
            _TestPaymentProducer(),
            TEST_REPORT_TEMP_DIR,
            10,
        )
        retry_producer.retry_failed_payments()

        self.assertEqual(1, len(payment_queue.queue))

        payment_batch = payment_queue.get()

        self.assertEqual(10, payment_batch.cycle)
        self.assertEqual(31, len(payment_batch.batch))
        self.assertEqual(
            5,
            len([row for row in payment_batch.batch if row.paid.is_fail()]),
        )

        nw = dict({"MINIMAL_BLOCK_DELAY": 30})
        payment_consumer = self.create_consumer(nw, payment_queue)
        payment_consumer._consume_batch(payment_batch)

        success_report = get_payment_report_file_path(TEST_REPORT_TEMP_DIR, 10, 0)
        self.assertTrue(os.path.isfile(success_report))

        success_report_rows = CsvPaymentFileParser().parse(success_report, 10)
        success_count = len([row for row in success_report_rows])
        hash_xxx_op_count = len(
            [
                row
                for row in success_report_rows
                if (row.hash is None or row.hash == "xxx_op_hash")
            ]
        )
        failed_reports_count = len(
            [
                file
                for file in os.listdir(os.path.join(TEST_REPORT_TEMP_DIR, "failed"))
                if os.path.isfile(file)
            ]
        )

        # Success is defined when the transactions are saved in the done folder
        self.assertEqual(31, success_count)
        self.assertEqual(5, hash_xxx_op_count)
        self.assertEqual(0, failed_reports_count)

    def tearDown(self):
        shutil.rmtree(TEST_REPORT_TEMP_DIR)

    @staticmethod
    def create_consumer(nw, payment_queue):
        return PaymentConsumer(
            "name",
            TEST_REPORT_TEMP_DIR,
            "tz1234567890123456789012345678901234",
            payment_queue,
            "node_addr",
            ClientManager("", ""),
            nw,
            MagicMock(),
            rewards_type=RewardsType.ACTUAL,
            dry_run=False,
        )


class _DummyRpcRewardApi:
    def update_current_balances(self, reward_logs):
        pass


class _TestPaymentProducer(PaymentProducerABC):
    def on_success(self, pymnt_batch):
        pass

    def on_fail(self, pymnt_batch):
        pass
