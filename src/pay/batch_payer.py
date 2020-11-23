import configparser
import os
from random import randint
from subprocess import TimeoutExpired
from time import sleep

import base58

from Constants import PaymentStatus
from log_config import main_logger, verbose_logger
from util.rpc_utils import parse_json_response

logger = main_logger

MAX_TX_PER_BLOCK = 200
PKH_LENGTH = 36
CONFIRMATIONS = 1
PATIENCE = 10

COMM_DELEGATE_BALANCE = "rpc get chains/main/blocks/{}/context/contracts/{}/balance"
COMM_HEAD = "rpc get /chains/main/blocks/head"
COMM_COUNTER = "rpc get /chains/main/blocks/head/context/contracts/{}/counter"
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"%fee%","counter":"%COUNTER%","gas_limit":"%gas_limit%","storage_limit":"%storage_limit%","amount":"%AMOUNT%"}'
FORGE_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
RUNOPS_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%], "signature":"edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"}'
PREAPPLY_JSON = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'
JSON_WRAP = '{"operation": %JSON%,"chain_id":"%chain_id%"}'
COMM_FORGE = "rpc post /chains/main/blocks/head/helpers/forge/operations with '%JSON%'"
COMM_RUNOPS = "rpc post /chains/main/blocks/head/helpers/scripts/run_operation with '%JSON%'"
COMM_PREAPPLY = "rpc post /chains/main/blocks/head/helpers/preapply/operations with '%JSON%'"
COMM_INJECT = "rpc post /injection/operation with '\"%OPERATION_HASH%\"'"
COMM_WAIT = "wait for %OPERATION% to be included --confirmations {}".format(CONFIRMATIONS)

FEE_INI = 'fee.ini'
MUTEZ = 1e6
RA_BURN_FEE = 257000  # 0.257 XTZ
RA_STORAGE = 300


class BatchPayer():
    def __init__(self, node_url, pymnt_addr, wllt_clnt_mngr, delegator_pays_ra_fee, delegator_pays_xfer_fee,
                 network_config, plugins_manager, dry_run):
        super(BatchPayer, self).__init__()
        self.pymnt_addr = pymnt_addr
        self.node_url = node_url
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.network_config = network_config
        self.zero_threshold = 1  # 1 mutez = 0.000001 XTZ
        self.plugins_manager = plugins_manager
        self.dry_run = dry_run

        config = configparser.ConfigParser()
        if os.path.isfile(FEE_INI):
            config.read(FEE_INI)
        else:
            logger.warn("File {} not found. Using default fee values".format(FEE_INI))

        kttx = config['KTTX']
        self.gas_limit = kttx['gas_limit']
        self.storage_limit = int(kttx['storage_limit'])
        self.default_fee = int(kttx['fee'])

        # section below is left to make sure no one using legacy configuration option
        self.delegator_pays_xfer_fee = config.getboolean('KTTX', 'delegator_pays_xfer_fee', fallback=True)  # Must use getboolean otherwise parses as string

        if not self.delegator_pays_xfer_fee:
            raise Exception("delegator_pays_xfer_fee is no longer read from fee.ini. It should be set in baking configuration file.")

        self.delegator_pays_ra_fee = delegator_pays_ra_fee
        self.delegator_pays_xfer_fee = delegator_pays_xfer_fee

        # If delegator pays the fee, then the cutoff should be transaction-fee + 1
        # Ex: Delegator reward is 1800 mutez, txn fee is 1792 mutez, reward - txn fee = 8 mutez payable reward
        #     If delegate pays fee, then cutoff is 1 mutez payable reward
        if self.delegator_pays_xfer_fee:
            self.zero_threshold += self.default_fee

        logger.info("Transfer fee is {:.6f} XTZ and is paid by {}".format(self.default_fee / MUTEZ, "Delegator" if self.delegator_pays_xfer_fee else "Delegate"))
        logger.info("Reactivation fee is {:.6f} XTZ and is paid by {}".format(RA_BURN_FEE / MUTEZ, "Delegator" if self.delegator_pays_ra_fee else "Delegate"))
        logger.info("Payment amount cutoff is {:.6f} XTZ".format(self.zero_threshold / MUTEZ))

        # If pymnt_addr has a length of 36 and starts with tz or KT then it is a public key, else it is an alias
        if len(self.pymnt_addr) == PKH_LENGTH and (
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

        self.comm_head = COMM_HEAD
        self.comm_counter = COMM_COUNTER.format(self.source)
        self.comm_runops = COMM_RUNOPS
        self.comm_forge = COMM_FORGE
        self.comm_preapply = COMM_PREAPPLY
        self.comm_inject = COMM_INJECT
        self.comm_wait = COMM_WAIT

    def pay(self, payment_items_in, dry_run=None):
        logger.info("{} payment items to process".format(len(payment_items_in)))

        # initialize the result list with already paid items
        payment_logs_paid = [pi for pi in payment_items_in if pi.paid == PaymentStatus.PAID]
        if payment_logs_paid:
            logger.info("{} payment items are already paid".format(len(payment_logs_paid)))

        payment_logs_done = [pi for pi in payment_items_in if pi.paid == PaymentStatus.DONE]
        if payment_logs_done:
            logger.info("{} payment items are already processed".format(len(payment_logs_done)))

        payment_logs_injected = [pi for pi in payment_items_in if pi.paid == PaymentStatus.INJECTED]
        if payment_logs_injected:
            logger.info("{} payment items are in injected status".format(len(payment_logs_injected)))

        payment_logs = []
        payment_logs.extend(payment_logs_paid)
        payment_logs.extend(payment_logs_done)
        payment_logs.extend(payment_logs_injected)

        self.log_processed_items(payment_logs)

        unprocessed_payment_items = [pi for pi in payment_items_in if not pi.paid.is_processed()]

        # all unprocessed_payment_items are important (non-trivial)
        # gather up all unprocessed_payment_items that are greater than, or equal to the zero_threshold
        # zero_threshold is either 1 mutez or the txn fee if delegator is not paying it, and burn fee
        payment_items = []
        sum_burn_fees = 0
        for pi in unprocessed_payment_items:

            zt = self.zero_threshold
            if pi.needs_activation and self.delegator_pays_ra_fee:
                # Need to apply this fee to only those which need reactivation
                zt += RA_BURN_FEE
                sum_burn_fees += RA_BURN_FEE

            if pi.amount >= zt:
                payment_items.append(pi)

        if not payment_items:
            logger.info("No payment items found, returning...")
            return payment_items_in, 0

        # split payments into lists of MAX_TX_PER_BLOCK or less size
        # [list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,...]
        payment_items_chunks = [payment_items[i:i + MAX_TX_PER_BLOCK] for i in
                                range(0, len(payment_items), MAX_TX_PER_BLOCK)]

        total_amount_to_pay = sum([pl.amount for pl in payment_items])
        total_amount_to_pay += sum_burn_fees
        if not self.delegator_pays_xfer_fee:
            total_amount_to_pay += self.default_fee * len(payment_items)

        payment_address_balance = self.__get_payment_address_balance()
        logger.info("Total amount to pay out is {:,} mutez.".format(total_amount_to_pay))
        logger.info("Current balance in payout address is {:,} mutez.".format(payment_address_balance))
        logger.info("{} payments will be done in {} batches".format(len(payment_items), len(payment_items_chunks)))

        if payment_address_balance is not None:

            number_future_payable_cycles = int(payment_address_balance / total_amount_to_pay) - 1

            if number_future_payable_cycles < 0:

                for pi in payment_items:
                    pi.paid = PaymentStatus.FAIL

                subject = "FAILED Payouts - Insufficient Funds"
                message = "Payment attempt failed because of insufficient funds in the payout address. " \
                          "The current balance, {:,} mutez, is insufficient to pay cycle rewards of {:,} mutez" \
                    .format(payment_address_balance, total_amount_to_pay)

                # Output to CLI, send notification using plugins
                logger.error(message)
                self.plugins_manager.send_notification(subject, message)

                # Exit early since nothing can be paid
                return payment_items, 0, 0

            elif number_future_payable_cycles < 1:

                subject = "Low Payment Address Funds Warning"
                message = "The payout address will soon run out of funds. The current balance, {:,} mutez, " \
                          "might not be sufficient for the next cycle".format(payment_address_balance)

                logger.warn(message)
                self.plugins_manager.send_notification(subject, message)

            else:
                logger.info("The payout account balance is expected to last for the next {:d} cycle(s)".format(number_future_payable_cycles))

        total_attempts = 0
        op_counter = OpCounter()

        for i_batch, payment_items_chunk in enumerate(payment_items_chunks):
            logger.debug("Payment of batch {} started".format(i_batch + 1))
            payments_log, attempt = self.pay_single_batch(payment_items_chunk, dry_run=dry_run, op_counter=op_counter)

            logger.info("Payment of batch {} is complete, in {} attempt(s)".format(i_batch + 1, attempt))

            payment_logs.extend(payments_log)
            total_attempts += attempt

        return payment_logs, total_attempts, number_future_payable_cycles

    def log_processed_items(self, payment_logs):
        if payment_logs:
            for pl in payment_logs:
                logger.debug("Reward already %s for cycle %s address %s amount %f tz type %s", pl.paid, pl.cycle, pl.address, pl.amount, pl.type)

    def pay_single_batch(self, payment_items, op_counter, dry_run=None):

        max_try = 3
        status = PaymentStatus.FAIL
        operation_hash = ""
        attempt_count = 0

        # for failed operations, trying after some time should be OK
        for attempt in range(max_try):
            try:
                status, operation_hash = self.attempt_single_batch(payment_items, op_counter, dry_run=dry_run)
            except Exception:
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
        block_time = self.network_config['BLOCK_TIME_IN_SEC']
        slp_tm = randint(block_time / 2, block_time)

        logger.debug("Wait for {} seconds before trying again".format(slp_tm))

        sleep(slp_tm)

    def attempt_single_batch(self, payment_records, op_counter, dry_run=None):
        if not op_counter.get():
            _, response = self.wllt_clnt_mngr.send_request(self.comm_counter)
            counter = parse_json_response(response)
            counter = int(counter)
            op_counter.set(counter)

        _, response = self.wllt_clnt_mngr.send_request(self.comm_head, verbose_override=False)
        head = parse_json_response(response)
        branch = head["hash"]
        chain_id = head["chain_id"]
        protocol = head["metadata"]["protocol"]

        logger.debug("head: branch {} counter {} protocol {}".format(branch, op_counter.get(), protocol))

        content_list = []

        for payment_item in payment_records:

            storage = self.storage_limit
            pymnt_amnt = payment_item.amount  # expects in micro tezos

            if payment_item.needs_activation:
                storage += RA_STORAGE
                if self.delegator_pays_ra_fee:
                    pymnt_amnt = max(pymnt_amnt - RA_BURN_FEE, 0)  # ensure not less than 0

            if self.delegator_pays_xfer_fee:
                pymnt_amnt = max(pymnt_amnt - self.default_fee, 0)  # ensure not less than 0

            # if pymnt_amnt becomes 0, don't pay
            if pymnt_amnt == 0:
                logger.debug("Payment to {} became 0 after deducting fees. Skipping.".format(payment_item.paymentaddress))
                continue

            op_counter.inc()

            content = CONTENT.replace("%SOURCE%", self.source).replace("%DESTINATION%", payment_item.paymentaddress) \
                .replace("%AMOUNT%", str(pymnt_amnt)).replace("%COUNTER%", str(op_counter.get())) \
                .replace("%fee%", str(self.default_fee)).replace("%gas_limit%", self.gas_limit).replace("%storage_limit%", str(storage))

            content_list.append(content)

            verbose_logger.info("Payment content: {}".format(content))

        contents_string = ",".join(content_list)

        # run the operations
        logger.debug("Running {} operations".format(len(content_list)))
        runops_json = RUNOPS_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        runops_json = JSON_WRAP.replace("%JSON%", runops_json).replace("%chain_id%", chain_id)
        runops_command_str = self.comm_runops.replace("%JSON%", runops_json)

        result, runops_command_response = self.wllt_clnt_mngr.send_request(runops_command_str)
        if not result:
            logger.error("Error in run_operation")
            logger.debug("Error in run_operation, request ->{}<-".format(runops_command_str))
            logger.debug("---")
            logger.debug("Error in run_operation, response ->{}<-".format(runops_command_response))
            return PaymentStatus.FAIL, ""

        # Parse result of run_operation and check for potential failures
        run_ops_parsed = parse_json_response(runops_command_response)

        # Check each contents object for failure
        for op in run_ops_parsed["contents"]:
            # https://docs.python.org/3/glossary.html#term-eafp
            try:
                op_status = op["metadata"]["operation_result"]["status"]
                if op_status == "failed":
                    op_error = op["metadata"]["operation_result"]["errors"][0]["id"]
                    logger.error("Error while validating operation - Status: {}, Message: {}".format(op_status, op_error))
                    return PaymentStatus.FAIL, ""
            except KeyError:
                logger.debug("Unable to find metadata->operation_result->{status,errors} in run_ops response")
                pass

        # forge the operations
        logger.debug("Forging {} operations".format(len(content_list)))
        forge_json = FORGE_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        forge_command_str = self.comm_forge.replace("%JSON%", forge_json)

        result, forge_command_response = self.wllt_clnt_mngr.send_request(forge_command_str)
        if not result:
            logger.error("Error in forge operation")
            logger.debug("Error in forge, request '{}'".format(forge_command_str))
            logger.debug("---")
            logger.debug("Error in forge, response '{}'".format(forge_command_response))
            return PaymentStatus.FAIL, ""

        # sign the operations
        bytes = parse_json_response(forge_command_response)
        signed_bytes = self.wllt_clnt_mngr.sign(bytes, self.manager_alias, verbose_override=True)

        # pre-apply operations
        logger.debug("Preapplying the operations")
        preapply_json = PREAPPLY_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string).replace("%PROTOCOL%", protocol).replace("%SIGNATURE%", signed_bytes)
        preapply_command_str = self.comm_preapply.replace("%JSON%", preapply_json)

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
        if dry_run:
            return PaymentStatus.DONE, ""

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

        result, inject_command_response = self.wllt_clnt_mngr.send_request(inject_command_str)
        if not result:
            logger.error("Error in inject operation")
            logger.debug("Error in inject, response '{}'".format(inject_command_str))
            logger.debug("---")
            logger.debug("Error in inject, response '{}'".format(inject_command_response))
            return PaymentStatus.FAIL, ""

        operation_hash = parse_json_response(inject_command_response)
        logger.info("Operation hash is {}".format(operation_hash))

        # wait for inclusion
        logger.info("Waiting for operation {} to be included. Please be patient until the block has {} confirmation(s)".format(operation_hash, CONFIRMATIONS))
        try:
            cmd = self.comm_wait.replace("%OPERATION%", operation_hash)
            self.wllt_clnt_mngr.send_request(cmd, timeout=self.get_confirmation_timeout())
            logger.info("Operation {} is included".format(operation_hash))
        except TimeoutExpired:
            logger.warn("Operation {} wait is timed out. Not sure about the result!".format(operation_hash))
            return PaymentStatus.INJECTED, operation_hash

        return PaymentStatus.PAID, operation_hash

    def get_confirmation_timeout(self):
        return self.network_config['BLOCK_TIME_IN_SEC'] * (CONFIRMATIONS + PATIENCE)

    def __get_payment_address_balance(self):
        payment_address_balance = None

        get_current_balance_request = COMM_DELEGATE_BALANCE.format("head", self.source)
        result, command_response = self.wllt_clnt_mngr.send_request(get_current_balance_request)
        payment_address_balance = parse_json_response(command_response)

        return int(payment_address_balance)


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
