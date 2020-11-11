import configparser
import os
from random import randint
from subprocess import TimeoutExpired
from time import sleep

import base58
import json

from Constants import PaymentStatus
from log_config import main_logger

logger = main_logger

MAX_TX_PER_BLOCK = 200
PKH_LENGTH = 36
PATIENCE = 10

COMM_DELEGATE_BALANCE = "/chains/main/blocks/{}/context/contracts/{}/balance"
COMM_HEAD = "/chains/main/blocks/head"
COMM_COUNTER = "/chains/main/blocks/head/context/contracts/{}/counter"
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"%fee%","counter":"%COUNTER%","gas_limit":"%gas_limit%","storage_limit":"%storage_limit%","amount":"%AMOUNT%"}'
FORGE_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
RUNOPS_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%], "signature":"edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"}'
PREAPPLY_JSON = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'
JSON_WRAP = '{"operation": %JSON%,"chain_id":"%chain_id%"}'

COMM_RUNOPS = "/chains/main/blocks/head/helpers/scripts/run_operation"
COMM_FORGE = "/chains/main/blocks/head/helpers/forge/operations"
COMM_PREAPPLY = "/chains/main/blocks/head/helpers/preapply/operations"
COMM_INJECT = "/injection/operation"
COMM_WAIT = "/chains/main/blocks/%BLOCK_HASH%/operation_hashes"

FEE_INI = 'fee.ini'
MUTEZ = 1e6
RA_BURN_FEE = 257000  # 0.257 XTZ
RA_STORAGE = 300


class BatchPayer():
    def __init__(self, node_url, pymnt_addr, wllt_clnt_mngr, delegator_pays_ra_fee, delegator_pays_xfer_fee, network_config, plugins_manager, dry_run):
        super(BatchPayer, self).__init__()
        self.pymnt_addr = pymnt_addr
        self.node_url = node_url
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.network_config = network_config
        self.zero_threshold = 1    # 1 mutez = 0.000001 XTZ
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
        self.delegator_pays_xfer_fee = config.getboolean('KTTX', 'delegator_pays_xfer_fee',
                                                         fallback=True)  # Must use getboolean otherwise parses as string

        if not self.delegator_pays_xfer_fee:
            raise Exception(
                "delegator_pays_xfer_fee is no longer read from fee.ini. It should be set in baking configuration file.")

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

    def pay(self, payment_items_in, verbose=None, dry_run=None):
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
        payment_items_chunks = [payment_items[i:i + MAX_TX_PER_BLOCK] for i in range(0, len(payment_items), MAX_TX_PER_BLOCK)]

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
            payments_log, attempt = self.pay_single_batch(payment_items_chunk, verbose=verbose, dry_run=dry_run, op_counter=op_counter)

            logger.info("Payment of batch {} is complete, in {} attempt(s)".format(i_batch + 1, attempt))

            payment_logs.extend(payments_log)
            total_attempts += attempt

        return payment_logs, total_attempts, number_future_payable_cycles

    def log_processed_items(self, payment_logs):
        if payment_logs:
            for pl in payment_logs:
                logger.debug("Reward already %s for cycle %s address %s amount %f tz type %s", pl.paid, pl.cycle, pl.address, pl.amount, pl.type)

    def pay_single_batch(self, payment_items, op_counter, verbose=None, dry_run=None):

        max_try = 3
        status = PaymentStatus.FAIL
        operation_hash = ""
        attempt_count = 0

        # for failed operations, trying after some time should be OK
        for attempt in range(max_try):
            try:
                status, operation_hash = self.attempt_single_batch(payment_items, op_counter, verbose, dry_run=dry_run)
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

    def attempt_single_batch(self, payment_records, op_counter, verbose=None, dry_run=None):
        if not op_counter.get():
            _,counter = self.wllt_clnt_mngr.request_url(self.comm_counter)
            counter = int(counter)
            op_counter.set(counter)

        _,head = self.wllt_clnt_mngr.request_url(self.comm_head, verbose_override=False)
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

            if verbose:
                logger.info("Payment content: {}".format(content))

        contents_string = ",".join(content_list)

        # run the operations
        logger.debug("Running {} operations".format(len(content_list)))
        runops_json = RUNOPS_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        runops_json = JSON_WRAP.replace("%JSON%", runops_json).replace("%chain_id%", chain_id)

        status, run_ops_parsed = self.wllt_clnt_mngr.request_url_post(self.comm_runops, runops_json, 'run_operation')
        if not (status == 200):
            logger.error("Error in run_operation")
            return PaymentStatus.FAIL, ""

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

        # if verbose: print("--> forge_command_str is |{}|".format(forge_command_str))

        status, bytes = self.wllt_clnt_mngr.request_url_post(self.comm_forge, forge_json)
        if not (status == 200):
            logger.error("Error in forge operation")
            return PaymentStatus.FAIL, ""

        # sign the operations
        signed_bytes = self.wllt_clnt_mngr.sign(bytes, self.manager_alias, verbose_override=True)

        # pre-apply operations
        logger.debug("Preapplying the operations")
        preapply_json = PREAPPLY_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string).replace("%PROTOCOL%", protocol).replace("%SIGNATURE%", signed_bytes)

        # if verbose: print("--> preapply_command_str is |{}|".format(preapply_command_str))

        status, preapply_command_response = self.wllt_clnt_mngr.request_url_post(self.comm_preapply, preapply_json)
        if not (status == 200):
            logger.error("Error in preapply operation")
            return PaymentStatus.FAIL, ""

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

        _, head = self.wllt_clnt_mngr.request_url(self.comm_head, verbose_override=False)
        last_level_before_injection = head['header']['level']

        status, operation_hash = self.wllt_clnt_mngr.request_url_post(self.comm_inject, json.dumps(signed_operation_bytes))
        if not (status == 200):
            logger.error("Error in inject operation")
            return PaymentStatus.FAIL, ""

        logger.info("Operation hash is {}".format(operation_hash))

        # wait for inclusion
        logger.info("Waiting for operation {} to be included...".format(operation_hash))
        for i in range(last_level_before_injection+1, last_level_before_injection+6):
            sleep(self.network_config['BLOCK_TIME_IN_SEC'])
            cmd = self.comm_wait.replace("%BLOCK_HASH%", 'head')
            status, list_op_hash = self.wllt_clnt_mngr.request_url(cmd, timeout=self.network_config['BLOCK_TIME_IN_SEC'] * PATIENCE)
            for op_hashes in list_op_hash:
                if operation_hash in op_hashes:
                    logger.info("Operation {} is included".format(operation_hash))
                    return PaymentStatus.PAID, operation_hash

        logger.warn("Operation {} wait is timed out. Not sure about the result!".format(operation_hash))
        return PaymentStatus.INJECTED, operation_hash

    def __get_payment_address_balance(self):
        get_current_balance_request = COMM_DELEGATE_BALANCE.format("head", self.source)
        status, payment_address_balance = self.wllt_clnt_mngr.request_url(get_current_balance_request)
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
