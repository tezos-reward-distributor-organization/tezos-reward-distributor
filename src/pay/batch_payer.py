import configparser
import os
from random import randint
from subprocess import TimeoutExpired
from time import sleep

import base58

from Constants import PaymentStatus
from NetworkConfiguration import BLOCK_TIME_IN_SEC
from log_config import main_logger
from util.rpc_utils import parse_json_response

ZERO_THRESHOLD = 2e-3

logger = main_logger

MAX_TX_PER_BLOCK = 284
PKH_LENGHT = 36
CONFIRMATIONS = 1
PATIENCE = 5

COMM_HEAD = " rpc get http://{}/chains/main/blocks/head"
COMM_COUNTER = " rpc get http://{}/chains/main/blocks/head/context/contracts/{}/counter"
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"%fee%","counter":"%COUNTER%","gas_limit": "%gas_limit%", "storage_limit": "%storage_limit%","amount":"%AMOUNT%"}'
FORGE_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
RUNOPS_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%], "signature":"edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"}'
PREAPPLY_JSON = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'
COMM_FORGE = " rpc post http://%NODE%/chains/main/blocks/head/helpers/forge/operations with '%JSON%'"
COMM_RUNOPS = " rpc post http://%NODE%/chains/main/blocks/head/helpers/scripts/run_operation with '%JSON%'"
COMM_PREAPPLY = " rpc post http://%NODE%/chains/main/blocks/head/helpers/preapply/operations with '%JSON%'"
COMM_INJECT = " rpc post http://%NODE%/injection/operation with '\"%OPERATION_HASH%\"'"
COMM_WAIT = " wait for %OPERATION% to be included --confirmations {}".format(CONFIRMATIONS)

FEE_INI = 'fee.ini'
DUMMY_FEE = 1000


class BatchPayer():
    def __init__(self, node_url, pymnt_addr, wllt_clnt_mngr, delegator_pays_xfer_fee, network_config):
        super(BatchPayer, self).__init__()
        self.pymnt_addr = pymnt_addr
        self.node_url = node_url
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.network_config = network_config

        config = configparser.ConfigParser()
        if os.path.isfile(FEE_INI):
            config.read(FEE_INI)
        else:
            logger.warn("File {} not found. Using default fee values".format(FEE_INI))

        kttx = config['KTTX']
        self.base = kttx['base']
        self.gas_limit = kttx['gas_limit']
        self.storage_limit = kttx['storage_limit']
        self.default_fee = kttx['fee']

        # section below is left to make sure no one using legacy configuration option
        self.delegator_pays_xfer_fee = config.getboolean('KTTX', 'delegator_pays_xfer_fee',
                                                         fallback=True)  # Must use getboolean otherwise parses as string

        if not self.delegator_pays_xfer_fee:
            raise Exception(
                "delegator_pays_xfer_fee is no longer read from fee.ini. It should be set in baking configuration file.")

        self.delegator_pays_xfer_fee = delegator_pays_xfer_fee

        logger.debug("Transfer fee is paid by {}".format("Delegator" if self.delegator_pays_xfer_fee else "Delegate"))

        # pymnt_addr has a length of 36 and starts with tz or KT then it is a public key has, else it is an alias
        if len(self.pymnt_addr) == PKH_LENGHT and (
                self.pymnt_addr.startswith("KT") or self.pymnt_addr.startswith("tz")):
            self.source = self.pymnt_addr
        else:
            known_contracts = self.wllt_clnt_mngr.get_known_contracts_by_alias()
            if self.pymnt_addr in known_contracts:
                self.source = known_contracts[self.pymnt_addr]
            else:
                raise Exception("pymnt_addr cannot be translated into a PKH or alias: {}".format(self.pymnt_addr))

        self.manager = self.wllt_clnt_mngr.get_addr_dict_by_pkh(self.source)['manager']
        self.manager_alias = self.wllt_clnt_mngr.get_addr_dict_by_pkh(self.manager)['alias']

        logger.debug("Payment address is {}".format(self.source))
        logger.debug("Signing address is {}, manager alias is {}".format(self.manager, self.manager_alias))

        self.comm_head = COMM_HEAD.format(self.node_url)
        self.comm_counter = COMM_COUNTER.format(self.node_url, self.source)
        self.comm_runops = COMM_RUNOPS.format().replace("%NODE%", self.node_url)
        self.comm_forge = COMM_FORGE.format().replace("%NODE%", self.node_url)
        self.comm_preapply = COMM_PREAPPLY.format().replace("%NODE%", self.node_url)
        self.comm_inject = COMM_INJECT.format().replace("%NODE%", self.node_url)
        self.comm_wait = COMM_WAIT.format()

    def pay(self, payment_items_in, verbose=None, dry_run=None):
        logger.info("{} payment items to process".format(len(payment_items_in)))

        # initialize the result list with already paid items
        payment_logs_paid = [pi for pi in payment_items_in if pi.paid==PaymentStatus.PAID]
        if payment_logs_paid:
            logger.info("{} payment items are already paid".format(len(payment_logs_paid)))

        payment_logs_done = [pi for pi in payment_items_in if pi.paid==PaymentStatus.DONE]
        if payment_logs_done:
            logger.info("{} payment items are already processed".format(len(payment_logs_done)))

        payment_logs_unknown = [pi for pi in payment_items_in if pi.paid==PaymentStatus.UNKNOWN]
        if payment_logs_unknown:
            logger.info("{} payment items are in unknown status".format(len(payment_logs_unknown)))

        payment_logs = []
        payment_logs.extend(payment_logs_paid)
        payment_logs.extend(payment_logs_done)
        payment_logs.extend(payment_logs_unknown)

        self.log_processed_items(payment_logs)

        payment_items = [pi for pi in payment_items_in if not pi.paid.is_processed()]

        # separate trivial items, amounts less than zero_threshold are not trivial, no needed to be paid
        non_trivial_payment_items = [pi for pi in payment_items if pi.amount < ZERO_THRESHOLD]
        non_trivial_payment_items_total = sum([pl.amount for pl in non_trivial_payment_items])
        if non_trivial_payment_items:
            logger.info("{} payment items are not trivial, total of {:,} mutez".format(len(non_trivial_payment_items), non_trivial_payment_items_total))
        self.log_non_trivial_items(non_trivial_payment_items)

        trivial_payment_items = [pi for pi in payment_items if pi.amount >= ZERO_THRESHOLD]
        if not trivial_payment_items:
            logger.debug("No trivial items found, returning...")
            return payment_items_in, 0

        # split payments into lists of MAX_TX_PER_BLOCK or less size
        # [list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,...]
        payment_items_chunks = [trivial_payment_items[i:i + MAX_TX_PER_BLOCK] for i in range(0, len(trivial_payment_items), MAX_TX_PER_BLOCK)]

        total_amount_to_pay = sum([pl.amount for pl in trivial_payment_items])
        if not self.delegator_pays_xfer_fee: total_amount_to_pay += int(self.default_fee) * len(trivial_payment_items)
        logger.info("Total trivial amount to pay is {:,} mutez.".format(total_amount_to_pay))
        logger.info("{} trivial payments will be done in {} batches".format(len(trivial_payment_items), len(payment_items_chunks)))

        total_attempts = 0
        op_counter = OpCounter()

        for i_batch, payment_items_chunk in enumerate(payment_items_chunks):
            logger.debug("Payment of batch {} started".format(i_batch + 1))
            payments_log, attempt = self.pay_single_batch(payment_items_chunk, verbose=verbose, dry_run=dry_run, op_counter=op_counter)

            logger.info("Payment of batch {} is complete, in {} attempt(s)".format(i_batch + 1, attempt))

            payment_logs.extend(payments_log)
            total_attempts += attempt

        # set non trivial items to DONE
        for pi in non_trivial_payment_items:
            pi.paid = PaymentStatus.DONE
            pi.hash = ""

        # add non trivial items
        payment_logs.extend(non_trivial_payment_items)

        return payment_logs, total_attempts

    def log_processed_items(self, payment_logs):
        if payment_logs:
            for pl in payment_logs:
                logger.debug("Reward already {} for cycle %s address %s amount %f tz type %s", pl.paid, pl.cycle, pl.address, pl.amount, pl.type)

    def log_non_trivial_items(self, payment_logs):
        if payment_logs:
            for pl in payment_logs:
                logger.debug("Reward not trivial for address %s amount %f tz type %s", pl.address, pl.amount, pl.type)

    def pay_single_batch(self, payment_items, op_counter, verbose=None, dry_run=None):

        max_try = 3
        status = PaymentStatus.FAIL
        operation_hash = ""
        attempt_count = 0

        # due to unknown reasons, some times a batch fails to pre-apply
        # trying after some time should be OK
        for attempt in range(max_try):
            try:
                status, operation_hash = self.attempt_single_batch(payment_items, op_counter, verbose, dry_run=dry_run)
            except:
                logger.error("batch payment attempt {}/{} for current batch failed with error".format(attempt + 1, max_try), exc_info=True)

            if dry_run or status.is_fail():
                op_counter.rollback()
            else:
                op_counter.commit()

            # we do not want to preserve counter anymore
            # force re-read of counter at every try
            op_counter.set(None)

            attempt_count += 1

            # if not fail, do not try anymore
            if not status.is_fail():
                break

            logger.debug("payment attempt {}/{} failed".format(attempt + 1, max_try))

            # But do not wait after last attempt
            if attempt < max_try - 1:
                self.wait_random()

        for payment_item in payment_items:
            payment_item.paid = status
            payment_item.hash = operation_hash

        return payment_items, attempt_count

    def wait_random(self):
        block_time = self.network_config[BLOCK_TIME_IN_SEC]
        slp_tm = randint(block_time / 2, block_time)

        logger.debug("Wait for {} seconds before trying again".format(slp_tm))

        sleep(slp_tm)

    def attempt_single_batch(self, payment_records, op_counter, verbose=None, dry_run=None):
        if not op_counter.get():
            _, response = self.wllt_clnt_mngr.send_request(self.comm_counter)
            counter = parse_json_response(response)
            counter = int(counter)
            op_counter.set(counter)

        _, response = self.wllt_clnt_mngr.send_request(self.comm_head, verbose_override=False)
        head = parse_json_response(response)
        branch = head["hash"]
        protocol = head["metadata"]["protocol"]

        logger.debug("head: branch {} counter {} protocol {}".format(branch, op_counter.get(), protocol))

        content_list = []

        for payment_item in payment_records:
            pymnt_amnt = payment_item.amount  # expects in micro tezos

            if self.delegator_pays_xfer_fee:
                pymnt_amnt = max(pymnt_amnt - int(self.default_fee), 0)  # ensure not less than 0

            assert pymnt_amnt >= ZERO_THRESHOLD # zero check, zero amounts needs to be filtered out earlier

            op_counter.inc()

            content = CONTENT.replace("%SOURCE%", self.source).replace("%DESTINATION%", payment_item.address) \
                .replace("%AMOUNT%", str(pymnt_amnt)).replace("%COUNTER%", str(op_counter.get())) \
                .replace("%fee%", self.default_fee).replace("%gas_limit%", self.gas_limit).replace("%storage_limit%", self.storage_limit)

            content_list.append(content)

            if verbose:
                logger.debug("Payment content: {}".format(content))

        contents_string = ",".join(content_list)

        # run the operations
        logger.debug("Running {} operations".format(len(content_list)))
        runops_json = RUNOPS_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        runops_command_str = self.comm_runops.replace("%JSON%", runops_json)

        # if verbose: print("--> runops_command_str is |{}|".format(runops_command_str))

        result, runops_command_response = self.wllt_clnt_mngr.send_request(runops_command_str)
        if not result:
            logger.error("Error in run_operation")
            logger.debug("Error in run_operation, request ->{}<-".format(runops_command_str))
            logger.debug("---")
            logger.debug("Error in run_operation, response ->{}<-".format(runops_command_response))
            return PaymentStatus.FAIL, ""

        # forge the operations
        logger.debug("Forging {} operations".format(len(content_list)))
        forge_json = FORGE_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        forge_command_str = self.comm_forge.replace("%JSON%", forge_json)

        #if verbose: print("--> forge_command_str is |{}|".format(forge_command_str))

        result, forge_command_response = self.wllt_clnt_mngr.send_request(forge_command_str)
        if not result:
            logger.error("Error in forge operation")
            logger.debug("Error in forge, request '{}'".format(forge_command_str))
            logger.debug("---")
            logger.debug("Error in forge, response '{}'".format(forge_command_response))
            return PaymentStatus.FAIL, ""

        # sign the operations
        bytes = parse_json_response(forge_command_response, verbose=verbose)
        signed_bytes = self.wllt_clnt_mngr.sign(bytes, self.manager_alias)

        # pre-apply operations
        logger.debug("Preapplying the operations")
        preapply_json = PREAPPLY_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string).replace("%PROTOCOL%", protocol).replace("%SIGNATURE%", signed_bytes)
        preapply_command_str = self.comm_preapply.replace("%JSON%", preapply_json)

        #if verbose: print("--> preapply_command_str is |{}|".format(preapply_command_str))

        result, preapply_command_response = self.wllt_clnt_mngr.send_request(preapply_command_str)
        if not result:
            logger.error("Error in preapply operation")
            logger.debug("Error in preapply, request '{}'".format(preapply_command_str))
            logger.debug("---")
            logger.debug("Error in preapply, response '{}'".format(preapply_command_response))

            return PaymentStatus.FAIL, ""

        # not necessary
        # preapplied = parse_response(preapply_command_response)

        # if dry_run, skip injection
        if dry_run: return PaymentStatus.DONE, ""

        # inject the operations
        logger.debug("Injecting {} operations".format(len(content_list)))
        decoded = base58.b58decode(signed_bytes).hex()

        if signed_bytes.startswith("edsig"):  # edsig signature
            decoded_edsig_signature = decoded[10:][:-8]  # first 5 bytes edsig, last 4 bytes checksum
            decoded_signature = decoded_edsig_signature
        elif signed_bytes.startswith("sig"):  # generic signature
            decoded_sig_signature = decoded[6:][:-8]  # first 3 bytes sig, last 4 bytes checksum
            decoded_signature = decoded_sig_signature
        elif signed_bytes.startswith("p2sig"):
            decoded_sig_signature = decoded[8:][:-8]  # first 4 bytes sig, last 4 bytes checksum
            decoded_signature = decoded_sig_signature
        else:
            raise Exception("Signature '{}' is not in expected format".format(signed_bytes))

        if len(decoded_signature) != 128:  # must be 64 bytes
            # raise Exception("Signature length must be 128 but it is {}. Signature is '{}'".format(len(signed_bytes), signed_bytes))
            logger.warn("Signature length must be 128 but it is {}. Signature is '{}'".format(len(signed_bytes), signed_bytes))
            # return False, ""

        signed_operation_bytes = bytes + decoded_signature
        inject_command_str = self.comm_inject.replace("%OPERATION_HASH%", signed_operation_bytes)

        #if verbose: print("--> inject_command_str is |{}|".format(inject_command_str))

        result, inject_command_response = self.wllt_clnt_mngr.send_request(inject_command_str)
        if not result:
            logger.error("Error in inject operation")
            logger.debug("Error in inject, response '{}'".format(inject_command_str))
            logger.debug("---")
            logger.debug("Error in inject, response '{}'".format(inject_command_response))
            return PaymentStatus.FAIL, ""

        operation_hash = parse_json_response(inject_command_response)
        logger.debug("Operation hash is {}".format(operation_hash))

        # wait for inclusion
        logger.debug("Waiting for operation {} to be included. Please be patient until the block has {} confirmation(s)".format(operation_hash, CONFIRMATIONS))
        try:
            cmd = self.comm_wait.replace("%OPERATION%", operation_hash)
            self.wllt_clnt_mngr.send_request(cmd, timeout=0.5*self.network_config[BLOCK_TIME_IN_SEC] * (CONFIRMATIONS + PATIENCE))
            logger.debug("Operation {} is included".format(operation_hash))
        except TimeoutExpired:
            logger.warn("Operation {} wait is timed out. Not sure about the result!".format(operation_hash))
            return PaymentStatus.UNKNOWN, operation_hash

        return PaymentStatus.PAID, operation_hash


class OpCounter:
    def __init__(self) -> None:
        super().__init__()
        self.__counter = None
        self.__counter_backup = None

    def inc(self):
        if self.__counter is None:
            raise Exception("Counter is not set!!!")

        self.__counter += 1

    def get(self):
        return self.__counter

    def commit(self):
        self.__counter_backup = self.__counter

    def rollback(self):
        self.__counter = self.__counter_backup

    def set(self, counter):
        self.__counter = counter
        self.__counter_backup = counter
