import os
import queue
import shutil
import unittest
from distutils.dir_util import copy_tree
from unittest import TestCase
from unittest.mock import patch, MagicMock
from Constants import PaymentStatus
from cli.client_manager import ClientManager
from pay.payment_consumer import PaymentConsumer
from pay.payment_producer_abc import PaymentProducerABC
from pay.retry_producer import RetryProducer
from util.csv_payment_file_parser import CsvPaymentFileParser
from util.dir_utils import payment_report_file_path


TEST_REPORT_DIR = "test_reports"
TEST_REPORT_TEMP_DIR = "test_reports_temp"


def request_url(url, timeout=None):
    print(url)
    if '/chains/main/blocks/head/context/contracts/' in url:
        return 200, 1
    if url == '/chains/main/blocks/head':
        return 200, dict({"header": dict({"level": 1000}), "hash": "hash", "chain_id": "unittest",
                          "metadata": dict({"protocol": "protocol1"})})
    if url == '/chains/main/blocks/head/operation_hashes':
        return 200, ["xxx_op_hash"]

    return "aaaaa" + str(timeout)


def request_url_post(cmd, json_params, timeout=None):
    print(cmd)
    if cmd == '/chains/main/blocks/head/helpers/scripts/run_operation':
        return 200, dict({"contents": [dict({"metadata": dict({"operation_result": dict({"status": "done"})})})]})
    if cmd == '/chains/main/blocks/head/helpers/forge/operations':
        return 200, "bytes"
    if cmd == '/chains/main/blocks/head/helpers/preapply/operations':
        return 200, "xxxx"
    if cmd == '/injection/operation':
        return 200, "xxx_op_hash"

    return "bbbb" + str(json_params) + str(timeout)


@unittest.skipIf('TRAVIS' in os.environ, 'Not running on Travis')
class TestRetryProducer(TestCase):
    def setUp(self):
        prepare_test_data()

    @patch('pay.payment_consumer.BatchPayer.get_payment_address_balance', MagicMock(return_value=100_000_000))
    @patch('pay.payment_consumer.BatchPayer.simulate_single_operation', MagicMock(return_value=(PaymentStatus.DONE, (500, 100, 0))))
    @patch('pay.batch_payer.sleep', MagicMock())
    @patch('cli.client_manager.ClientManager.request_url', MagicMock(side_effect=request_url))
    @patch('cli.client_manager.ClientManager.request_url_post', MagicMock(side_effect=request_url_post))
    @patch('cli.client_manager.ClientManager.sign', MagicMock(return_value="edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"))
    def test_retry_failed_payments(self):
        payment_queue = queue.Queue(100)

        retry_producer = RetryProducer(payment_queue, _DummyRpcRewardApi(), _TestPaymentProducer(),
                                       TEST_REPORT_TEMP_DIR)
        retry_producer.retry_failed_payments()

        self.assertEqual(1, len(payment_queue.queue))

        payment_batch = payment_queue.get()

        self.assertEqual(10, payment_batch.cycle)
        self.assertEqual(31, len(payment_batch.batch))
        self.assertEqual(5, len([row for row in payment_batch.batch if row.paid == PaymentStatus.FAIL]))

        nw = dict({'BLOCK_TIME_IN_SEC': 64})
        payment_consumer = self.create_consumer(nw, payment_queue)
        payment_consumer._consume_batch(payment_batch)

        success_report = payment_report_file_path(TEST_REPORT_TEMP_DIR, 10, 0)
        self.assertTrue(os.path.isfile(success_report))

        success_report_rows = CsvPaymentFileParser().parse(success_report, 10)
        nb_success = len([row for row in success_report_rows if row.paid == PaymentStatus.PAID])
        nb_hash_xxx_op_hash = len([row for row in success_report_rows if row.hash == 'xxx_op_hash'])

        self.assertEqual(31, nb_success)
        self.assertEqual(5, nb_hash_xxx_op_hash)

    @staticmethod
    def create_consumer(nw, payment_queue):
        return PaymentConsumer("name", TEST_REPORT_TEMP_DIR, "tz1234567890123456789012345678901234", payment_queue,
                               "node_addr", ClientManager('', ''), nw, MagicMock(),
                               rewards_type='actual', dry_run=False)


def prepare_test_data():
    try:
        shutil.rmtree(TEST_REPORT_TEMP_DIR)
    except OSError:
        pass
    copy_tree(TEST_REPORT_DIR, TEST_REPORT_TEMP_DIR)


class _DummyRpcRewardApi:
    def update_current_balances(self, reward_logs):
        pass


class _TestPaymentProducer(PaymentProducerABC):
    def on_success(self, pymnt_batch):
        pass

    def on_fail(self, pymnt_batch):
        pass
