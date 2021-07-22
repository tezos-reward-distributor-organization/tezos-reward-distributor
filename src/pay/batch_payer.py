import configparser
import os
from random import randint
from time import sleep
from http import HTTPStatus

import base58
import json
import math

from Constants import PaymentStatus, MUTEZ
from log_config import main_logger, verbose_logger

logger = main_logger

MAX_TX_PER_BLOCK_TZ = 400
MAX_TX_PER_BLOCK_KT = 10
PKH_LENGTH = 36
SIGNATURE_BYTES_SIZE = 64
MAX_NUM_TRIALS_PER_BLOCK = 2
MAX_BLOCKS_TO_CHECK_AFTER_INJECTION = 5

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
RA_BURN_FEE = 257000  # 0.257 XTZ
RA_STORAGE = 300

# This fee limit is set to allow payouts to ovens
# Other KT accounts with higher fee requirements will be skipped
# TODO: define set of known contract formats and make this fee for unknown contracts configurable
FEE_LIMIT_CONTRACTS = 100000

KT1_FEE_SAFETY_CHECK = True

# For simulation
HARD_GAS_LIMIT_PER_OPERATION = 1040000
HARD_STORAGE_LIMIT_PER_OPERATION = 60000

COST_PER_BYTE = 250
MINIMUM_FEE_MUTEZ = 100
MUTEZ_PER_GAS_UNIT = 0.1
MUTEZ_PER_BYTE = 1


class BatchPayer():
    def __init__(self, node_url, pymnt_addr, clnt_mngr, delegator_pays_ra_fee, delegator_pays_xfer_fee,
                 network_config, plugins_manager, dry_run):
        self.pymnt_addr = pymnt_addr
        self.node_url = node_url
        self.clnt_mngr = clnt_mngr
        self.network_config = network_config
        self.zero_threshold = 1  # 1 mutez = 0.000001 XTZ
        self.plugins_manager = plugins_manager
        self.dry_run = dry_run

        config = configparser.ConfigParser()
        if os.path.isfile(FEE_INI):
            config.read(FEE_INI)
        else:
            logger.warning("File {} not found. Using default fee values".format(FEE_INI))

        tztx = config['TZTX']
        self.gas_limit = tztx['gas_limit']
        self.storage_limit = int(tztx['storage_limit'])
        self.default_fee = int(tztx['fee'])

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

        logger.info("Transfer fee is {:.6f} XTZ and is paid by {}".format(self.default_fee / MUTEZ,
                                                                          "Delegator" if self.delegator_pays_xfer_fee else "Delegate"))
        logger.info("Reactivation fee is {:.6f} XTZ and is paid by {}".format(RA_BURN_FEE / MUTEZ,
                                                                              "Delegator" if self.delegator_pays_ra_fee else "Delegate"))
        logger.info("Payment amount minimum is {:.6f} XTZ".format(self.zero_threshold / MUTEZ))

        # If pymnt_addr has a length of 36 and starts with tz or KT then it is a public key, else it is an alias
        if len(self.pymnt_addr) == PKH_LENGTH and (
                self.pymnt_addr.startswith("KT") or self.pymnt_addr.startswith("tz")):
            self.source = self.pymnt_addr
        else:
            known_contracts = self.clnt_mngr.get_known_contracts_by_alias()
            if self.pymnt_addr in known_contracts:
                self.source = known_contracts[self.pymnt_addr]
            else:
                raise Exception("pymnt_addr cannot be translated into a PKH or alias: {}".format(self.pymnt_addr))

        self.manager = self.source
        logger.debug("Payment address is {}".format(self.source))

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

            # Reinitialize status for items fetched from failed payment files
            if pi.paid == PaymentStatus.FAIL:
                pi.paid = PaymentStatus.UNDEFINED

            # Check if payment item was skipped due to any of the phase calculations.
            # Add any items which are marked as skipped to the returning array so that they are logged to reports.
            if not pi.payable:
                logger.info("Skipping payout to {:s} {:>10.6f}, reason: {:s}".format(pi.address, pi.amount / MUTEZ, pi.desc))
                payment_logs.append(pi)
                continue

            zt = self.zero_threshold
            if pi.needs_activation and self.delegator_pays_ra_fee:
                # Need to apply this fee to only those which need reactivation
                zt += RA_BURN_FEE

                # Check here if payout amount is greater than, or equal to new zero threshold with reactivation fee added.
                # If so, add burn fee to global total. If not, payout will not get appended to list and therefor burn fee should not be added to global total.
                if pi.amount >= zt:
                    sum_burn_fees += RA_BURN_FEE

            # If payout total greater than, or equal to zero threshold, append payout record to master array
            if pi.amount >= zt:
                payment_items.append(pi)
            else:
                logger.info("Skipping payout to {:s} ({:>10.6f} XTZ), reason: payout below minimum ({:>10.6f} XTZ)".format(pi.address, pi.amount / MUTEZ, zt / MUTEZ))

        if not payment_items:
            logger.info("No payment items found, returning...")
            return payment_items_in, 0, 0, 0

        # split payments into lists of MAX_TX_PER_BLOCK or less size
        # [list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,...]
        payment_items_tz = [payment_item for payment_item in payment_items if payment_item.paymentaddress.startswith('tz')]
        payment_items_KT = [payment_item for payment_item in payment_items if payment_item.paymentaddress.startswith('KT')]
        payment_items_chunks_tz = [payment_items_tz[i:i + MAX_TX_PER_BLOCK_TZ] for i in
                                   range(0, len(payment_items_tz), MAX_TX_PER_BLOCK_TZ)]
        payment_items_chunks_KT = [payment_items_KT[i:i + MAX_TX_PER_BLOCK_KT] for i in
                                   range(0, len(payment_items_KT), MAX_TX_PER_BLOCK_KT)]
        payment_items_chunks = payment_items_chunks_tz + payment_items_chunks_KT

        total_amount_to_pay = sum([pl.amount for pl in payment_items])
        total_amount_to_pay += sum_burn_fees
        if not self.delegator_pays_xfer_fee:
            total_amount_to_pay += self.default_fee * len(payment_items)

        payment_address_balance = self.get_payment_address_balance()
        logger.info("Total amount to pay out is {:,} mutez.".format(total_amount_to_pay))
        logger.info("{} payments will be done in {} batches".format(len(payment_items), len(payment_items_chunks)))

        if payment_address_balance is not None:

            logger.info("Current balance in payout address is {:,} mutez.".format(payment_address_balance))

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
                self.plugins_manager.send_admin_notification(subject, message)

                # Exit early since nothing can be paid
                return payment_items, 0, 0, 0

            elif number_future_payable_cycles < 1:

                subject = "WARNING Payouts - Low Payment Address Funds"
                message = "The payout address will soon run out of funds. The current balance, {:,} mutez, " \
                          "might not be sufficient for the next cycle".format(payment_address_balance)

                logger.warning(message)
                self.plugins_manager.send_admin_notification(subject, message)

            else:
                logger.info("The payout account balance is expected to last for the next {:d} cycle(s)".format(
                    number_future_payable_cycles))

        total_attempts = 0
        op_counter = OpCounter()

        for i_batch, payment_items_chunk in enumerate(payment_items_chunks):
            logger.debug("Payment of batch {} started".format(i_batch + 1))
            payments_log, attempt = self.pay_single_batch(payment_items_chunk, dry_run=dry_run, op_counter=op_counter)

            logger.info("Payment of batch {} is complete, in {} attempt(s)".format(i_batch + 1, attempt))

            payment_logs.extend(payments_log)
            total_attempts += attempt

        return payment_logs, total_attempts, total_amount_to_pay, number_future_payable_cycles

    def log_processed_items(self, payment_logs):
        if payment_logs:
            for pl in payment_logs:
                logger.debug("Reward already %s for cycle %s address %s amount %f tz type %s", pl.paid, pl.cycle,
                             pl.address, pl.amount, pl.type)

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
                logger.error(
                    "batch payment attempt {}/{} for current batch failed with error".format(attempt + 1, max_try),
                    exc_info=True)

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
            if payment_item.paid == PaymentStatus.UNDEFINED:
                payment_item.paid = status
                payment_item.hash = operation_hash

        return payment_items, attempt_count

    def wait_random(self):
        block_time = self.network_config['BLOCK_TIME_IN_SEC']
        slp_tm = randint(block_time // 2, block_time)

        logger.debug("Wait for {} seconds before trying again".format(slp_tm))

        sleep(slp_tm)

    def simulate_single_operation(self, payment_item, pymnt_amnt, branch, chain_id):
        # Initial gas, storage and transaction limits
        gas_limit = str(HARD_GAS_LIMIT_PER_OPERATION)
        storage_limit = str(HARD_STORAGE_LIMIT_PER_OPERATION)
        tx_fee = self.default_fee

        content = CONTENT.replace("%SOURCE%", self.source).replace("%DESTINATION%", payment_item.paymentaddress) \
            .replace("%AMOUNT%", str(pymnt_amnt)).replace("%COUNTER%", str(self.base_counter + 1)) \
            .replace("%fee%", str(tx_fee)).replace("%gas_limit%", gas_limit) \
            .replace("%storage_limit%", storage_limit)

        runops_json = RUNOPS_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", content)
        runops_json = JSON_WRAP.replace("%JSON%", runops_json).replace("%chain_id%", chain_id)

        status, run_ops_parsed = self.clnt_mngr.request_url_post(cmd=self.comm_runops,
                                                                 json_params=runops_json)
        if status != HTTPStatus.OK:
            logger.error("Error in run_operation")
            return PaymentStatus.FAIL, []

        consumed_storage = 0

        op = run_ops_parsed["contents"][0]
        status = op["metadata"]["operation_result"]["status"]
        if status == 'applied':

            # Calculate actual consumed gas amount
            consumed_gas = int(op["metadata"]["operation_result"]["consumed_gas"])
            if "internal_operation_results" in op["metadata"]:
                internal_operation_results = op["metadata"]["internal_operation_results"]
                for internal_op in internal_operation_results:
                    consumed_gas += int(internal_op['result']['consumed_gas'])

            # Calculate actual used storage
            if 'paid_storage_size_diff' in op['metadata']['operation_result']:
                consumed_storage += int(op['metadata']['operation_result']['paid_storage_size_diff'])
            if "internal_operation_results" in op["metadata"]:
                internal_operation_results = op["metadata"]["internal_operation_results"]
                for internal_op in internal_operation_results:
                    if 'paid_storage_size_diff' in internal_op['result']:
                        consumed_storage += int(internal_op['result']['paid_storage_size_diff'])

        else:
            op_error = "Unknown error in simulating contract payout. Payment will be skipped!"
            if "errors" in op["metadata"]["operation_result"] and len(op["metadata"]["operation_result"]["errors"]) > 0 and "id" in op["metadata"]["operation_result"]["errors"][0]:
                op_error = op["metadata"]["operation_result"]["errors"][0]["id"]
            logger.error("Error while validating operation - Status: {}, Message: {}".format(status, op_error))
            return PaymentStatus.FAIL, []

        # Calculate needed fee for extra consumed gas
        tx_fee += int(consumed_gas * MUTEZ_PER_GAS_UNIT)
        simulation_results = consumed_gas, tx_fee, consumed_storage

        return PaymentStatus.DONE, simulation_results

    def attempt_single_batch(self, payment_records, op_counter, dry_run=None):
        if not op_counter.get():
            status, counter = self.clnt_mngr.request_url(self.comm_counter)
            if status != HTTPStatus.OK:
                raise Exception("Received response code {} for request '{}'".format(status, self.comm_counter))
            counter = int(counter)
            self.base_counter = int(counter)
            op_counter.set(self.base_counter)

        _, head = self.clnt_mngr.request_url(self.comm_head)
        branch = head["hash"]
        chain_id = head["chain_id"]
        protocol = head["metadata"]["protocol"]

        logger.debug("head: branch {} counter {} protocol {}".format(branch, op_counter.get(), protocol))

        content_list = []

        total_gas = total_fees = 0

        for payment_item in payment_records:

            pymnt_amnt = payment_item.amount  # expected in micro tez
            storage_limit, gas_limit, tx_fee = self.storage_limit, self.gas_limit, self.default_fee

            # TRD extension for non scriptless contract accounts
            if payment_item.paymentaddress.startswith('KT'):
                simulation_status, simulation_results = self.simulate_single_operation(payment_item, pymnt_amnt, branch, chain_id)
                if simulation_status == PaymentStatus.FAIL:
                    logger.info("Payment to {} script could not be processed. Possible reason: liquidated contract. Skipping. Think about redirecting the payout to the owner address using the maps rules. Please refer to the TRD documentation or to one of the TRD maintainers."
                                .format(payment_item.paymentaddress))
                    payment_item.paid = PaymentStatus.AVOIDED
                    continue
                gas_limit, tx_fee, storage_limit = simulation_results
                burn_fee = COST_PER_BYTE * storage_limit
                total_fee = tx_fee + burn_fee

                if KT1_FEE_SAFETY_CHECK:
                    if total_fee > FEE_LIMIT_CONTRACTS:
                        logger.info("Payment to {:s} script requires higher fees than reward amount. Skipping. Needed fee: {:10.6f} XTZ, max fee: {:10.6f} XTZ. Either configure a higher fee or redirect to the owner address using the maps rules. Refer to the TRD documentation."
                                    .format(payment_item.paymentaddress, total_fee / MUTEZ, FEE_LIMIT_CONTRACTS / MUTEZ))
                        payment_item.paid = PaymentStatus.AVOIDED
                        continue

                    if total_fee > pymnt_amnt:
                        logger.info("Payment to {:s} requires fees of {:10.6f} higher than payment amount of {:10.6f}."
                                    "Payment avoided due KT1_FEE_SAFETY_CHECK set to True.".format(payment_item.paymentaddress,
                                                                                                   total_fee / MUTEZ, pymnt_amnt / MUTEZ))
                        payment_item.paid = PaymentStatus.AVOIDED
                        continue

                # Subtract burn fee from the payment amount
                orig_pymnt_amnt = pymnt_amnt
                pymnt_amnt = max(pymnt_amnt - burn_fee, 0)  # ensure not less than 0
                logger.info("Payment to {} script requires {:.0f} gas * {:.2f} mutez-per-gas + {:10.6f} burn fee; Payment reduced from {:10.6f} to {:10.6f}".format(
                            payment_item.paymentaddress, gas_limit, MUTEZ_PER_GAS_UNIT, burn_fee / MUTEZ, orig_pymnt_amnt / MUTEZ, pymnt_amnt / MUTEZ))

            else:
                # An implicit tz1 account
                if payment_item.needs_activation:
                    storage_limit += RA_STORAGE
                    if self.delegator_pays_ra_fee:
                        # Subtract reactivation fee from the payment amount
                        orig_pymnt_amnt = pymnt_amnt
                        pymnt_amnt = max(pymnt_amnt - RA_BURN_FEE, 0)  # ensure not less than 0
                        logger.info("Payment to {:s} reduced from {:>10.6f} to {:>10.6f} due to reactivation fee".format(payment_item.address, orig_pymnt_amnt / MUTEZ, pymnt_amnt / MUTEZ))

            # Subtract transaction's fee from the payment amount if delegator has to pay for it
            if self.delegator_pays_xfer_fee:
                pymnt_amnt = max(pymnt_amnt - tx_fee, 0)  # ensure not less than 0

            # Resume main logic

            # if pymnt_amnt becomes 0, don't pay
            if pymnt_amnt == 0:
                payment_item.paid = PaymentStatus.DONE
                logger.info("Payment to {:s} became 0 after deducting fees. Skipping.".format(payment_item.paymentaddress))
                continue
            else:
                logger.debug("Payment to {:s} became {:10.6f} after deducting fees.".format(payment_item.paymentaddress, pymnt_amnt / MUTEZ))

            op_counter.inc()

            total_gas += int(gas_limit)
            total_fees += int(tx_fee)

            content = CONTENT.replace("%SOURCE%", self.source) \
                .replace("%DESTINATION%", payment_item.paymentaddress) \
                .replace("%AMOUNT%", str(pymnt_amnt)) \
                .replace("%COUNTER%", str(op_counter.get())) \
                .replace("%fee%", str(tx_fee)) \
                .replace("%gas_limit%", str(gas_limit)) \
                .replace("%storage_limit%", str(storage_limit))

            content_list.append(content)

            verbose_logger.info("Payment content: {}".format(content))

        if len(content_list) == 0:
            return PaymentStatus.DONE, ""
        contents_string = ",".join(content_list)

        # run the operations
        logger.debug("Running {} operations".format(len(content_list)))
        runops_json = RUNOPS_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        runops_json = JSON_WRAP.replace("%JSON%", runops_json).replace("%chain_id%", chain_id)

        status, run_ops_parsed = self.clnt_mngr.request_url_post(self.comm_runops, runops_json)
        if status != HTTPStatus.OK:
            logger.error("Error in run_operation")
            return PaymentStatus.FAIL, ""

        # Check each contents object for failure
        for op in run_ops_parsed["contents"]:
            # https://docs.python.org/3/glossary.html#term-eafp
            try:
                op_status = op["metadata"]["operation_result"]["status"]
                if op_status == "failed":
                    op_error = op["metadata"]["operation_result"]["errors"][0]["id"]
                    logger.error(
                        "Error while validating operation - Status: {}, Message: {}".format(op_status, op_error))
                    return PaymentStatus.AVOIDED, ""
            except KeyError:
                logger.debug("Unable to find metadata->operation_result->{status,errors} in run_ops response")

        # forge the operations
        logger.debug("Forging {} operations".format(len(content_list)))
        forge_json = FORGE_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)

        # if verbose: print("--> forge_command_str is |{}|".format(forge_command_str))

        status, bytes = self.clnt_mngr.request_url_post(self.comm_forge, forge_json)
        if status != HTTPStatus.OK:
            logger.error("Error in forge operation")
            return PaymentStatus.FAIL, ""
        size = SIGNATURE_BYTES_SIZE + len(bytes) / 2
        required_fee = math.ceil(MINIMUM_FEE_MUTEZ + MUTEZ_PER_GAS_UNIT * total_gas + MUTEZ_PER_BYTE * size)
        logger.info(f'minimal required fee is {required_fee}, current used fee is {total_fees}')

        while total_fees < required_fee:
            difference_fees = int(math.ceil(required_fee - total_fees))
            first_tx = json.loads(content_list[0])
            first_tx['fee'] = str(int(int(first_tx['fee']) + difference_fees))
            total_fees = required_fee
            content_list[0] = json.dumps(first_tx)
            contents_string = ",".join(content_list)
            forge_json = FORGE_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
            status, bytes = self.clnt_mngr.request_url_post(self.comm_forge, forge_json)
            if status != HTTPStatus.OK:
                logger.error("Error in forge operation")
                return PaymentStatus.FAIL, ""
            size = SIGNATURE_BYTES_SIZE + len(bytes) / 2
            required_fee = math.ceil(MINIMUM_FEE_MUTEZ + MUTEZ_PER_GAS_UNIT * total_gas + MUTEZ_PER_BYTE * size)
            logger.info(f'minimal required fee is {required_fee}, current used fee is {total_fees}')

        signed_bytes = self.clnt_mngr.sign(bytes, self.manager)

        # pre-apply operations
        logger.debug("Preapplying the operations")
        preapply_json = PREAPPLY_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string).replace("%PROTOCOL%", protocol).replace("%SIGNATURE%", signed_bytes)

        # if verbose: print("--> preapply_command_str is |{}|".format(preapply_command_str))

        status, preapply_command_response = self.clnt_mngr.request_url_post(self.comm_preapply, preapply_json)
        if status != HTTPStatus.OK:
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
            logger.warn(
                "Signature length must be 128 but it is {}. Signature is '{}'".format(len(signed_bytes), signed_bytes))
            # return False, ""

        signed_operation_bytes = bytes + decoded_signature

        _, head = self.clnt_mngr.request_url(self.comm_head)
        last_level_before_injection = head['header']['level']

        status, operation_hash = self.clnt_mngr.request_url_post(self.comm_inject,
                                                                 json.dumps(signed_operation_bytes))
        if status != HTTPStatus.OK:
            logger.error("Error in inject operation")
            return PaymentStatus.FAIL, ""

        logger.info("Operation hash is {}".format(operation_hash))

        # wait for inclusion
        timeout = MAX_BLOCKS_TO_CHECK_AFTER_INJECTION * MAX_NUM_TRIALS_PER_BLOCK * self.network_config['BLOCK_TIME_IN_SEC'] // 60
        logger.info("Waiting for operation {} to be included... Please do not interrupt the process!!! (Timeout is around {} minutes)".format(operation_hash, timeout))
        for i in range(last_level_before_injection + 1, last_level_before_injection + 1 + MAX_BLOCKS_TO_CHECK_AFTER_INJECTION):
            cmd = self.comm_wait.replace("%BLOCK_HASH%", str(i))
            status = -1
            list_op_hash = []
            trial_i = 0
            while status != HTTPStatus.OK and (trial_i < MAX_NUM_TRIALS_PER_BLOCK):
                sleep(self.network_config['BLOCK_TIME_IN_SEC'])
                status, list_op_hash = self.clnt_mngr.request_url(cmd)
                trial_i += 1
            if status != HTTPStatus.OK:
                logger.warning("Level {} could not be queried about operation hashes".format(i))
                break
            for op_hashes in list_op_hash:
                if operation_hash in op_hashes:
                    logger.info("Operation {} is included".format(operation_hash))
                    return PaymentStatus.PAID, operation_hash
            logger.debug("Operation {} is not included at level {}".format(operation_hash, i))

        logger.warning("Operation {} wait is timed out. Not sure about the result!".format(operation_hash))
        return PaymentStatus.INJECTED, operation_hash

    def get_payment_address_balance(self):
        get_current_balance_request = COMM_DELEGATE_BALANCE.format("head", self.source)
        status, payment_address_balance = self.clnt_mngr.request_url(get_current_balance_request)

        if status != HTTPStatus.OK:
            logger.warning("Balance request failed! Response code {} is received for request '{}'. See verbose logs for more detail.".format(status, get_current_balance_request))
            return None

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
