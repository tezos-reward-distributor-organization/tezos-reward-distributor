from http import HTTPStatus
from time import sleep
import base58
import json
import math

from log_config import main_logger, verbose_logger
from Constants import PaymentStatus

from pay.utils import (
    calculate_required_fee,
    calculate_tx_fee,
    log_and_fail,
    build_runops_json_params,
    calculate_consumed_gas,
    calculate_consumed_storage,
    init_payment_logs,
    calculate_estimated_amount_to_pay,
    sort_and_chunk_payment_items,
    calculate_future_payable_cycles,
)

from util.wait_random import wait_random

from util.address_validator import AddressValidator

from util.exit_program import ExitCode

logger = main_logger

# General transaction parameters:
#
# This fee limit is set to allow payouts to ovens
# Other KT accounts with higher fee requirements will be skipped
# TODO: define set of known contract formats and make this fee for unknown contracts configurable
KT1_FEE_SAFETY_CHECK = True
FEE_LIMIT_CONTRACTS = 100000
ZERO_THRESHOLD = 1  # too less to payout in mutez

# For simulation
# https://rpc.tzkt.io/mainnet/chains/main/blocks/head/context/constants
HARD_GAS_LIMIT_PER_OPERATION = 1040000
HARD_STORAGE_LIMIT_PER_OPERATION = 60000
COST_PER_BYTE = 250
MINIMUM_FEE_MUTEZ = 100
MUTEZ_PER_GAS_UNIT = 0.1
MUTEZ_PER_BYTE = 1

PKH_LENGTH = 36
SIGNATURE_BYTES_SIZE = 64
MAX_NUM_TRIALS_PER_BLOCK = 2
MAX_BLOCKS_TO_CHECK_AFTER_INJECTION = 5
MAX_BATCH_PAYMENT_ATTEMPTS = 3

COMM_DELEGATE_BALANCE = "/chains/main/blocks/{}/context/contracts/{}/balance"
COMM_PAYMENT_HEAD = "/chains/main/blocks/head~10"
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

# Lima
# Non-allocated:
#   The contract does not exist and needs some more gas (and fees) to pay up for the used storage.
#   If a delegate empties its account it gets removed from the storage. However, if it is expected
#   to receive a reward then you would need to pay up again for the storage to re-allocated its
#   account which is costlier than a simple transfer.
# Not revealed:
#   A state of a contract that did not yet publish its public key but in order to enact a delegation you need to be revealed.
#
# These values may change with protocol upgrades
TX_FEES = {
    "TZ1_TO_ALLOCATED_TZ1": {
        "FEE": 298,
        "GAS_LIMIT": 3400,
        "STORAGE_LIMIT": 0,  # 65 mutez before
    },
    "TZ1_TO_NON_ALLOCATED_TZ1": {
        "FEE": 397,
        "GAS_LIMIT": 3421,
        "STORAGE_LIMIT": 277,
        "BURN_FEE": None,  # 0.257 tez before
    },
    "TZ1_REVEAL": {
        "FEE": 357,
        "GAS_LIMIT": 3400,
        "STORAGE_LIMIT": 0,
    },
}

# TODO: We need to refactor the whole class and all its functions.
# Procedure needs to be transitioned to:
# 1) Calculate all payments
# 2) Simulate all fees
# 3) Sort and exclude payments due to e.g. too high fees or too small payment amount
# 4) Create batches
# 5) Inject payments


class BatchPayer:
    def __init__(
        self,
        node_url,
        pymnt_addr,
        clnt_mngr,
        delegator_pays_ra_fee,
        delegator_pays_xfer_fee,
        network_config,
        plugins_manager,
        dry_run,
    ):
        self.pymnt_addr = pymnt_addr
        self.node_url = node_url
        self.clnt_mngr = clnt_mngr
        self.network_config = network_config
        self.default_zero_threshold = int(ZERO_THRESHOLD)
        self.plugins_manager = plugins_manager
        self.dry_run = dry_run

        # Default tz1 to tz1 transaction fees
        self.default_gas_limit = int(TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["GAS_LIMIT"])
        self.default_storage_limit = int(
            TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["STORAGE_LIMIT"]
        )
        self.default_fee = int(TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"])
        TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["BURN_FEE"] = int(
            TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["STORAGE_LIMIT"] * COST_PER_BYTE
        )

        self.delegator_pays_ra_fee = delegator_pays_ra_fee
        self.delegator_pays_xfer_fee = delegator_pays_xfer_fee

        # If delegator pays the fee, then the cutoff should be transaction-fee + 1
        # Fixed value can only be used to determine threshold for tz addresses
        # Ex: Delegator reward is 1800 mutez, txn fee is 1792 mutez, reward - txn fee = 8 mutez payable reward
        #     If delegate pays fee, then cutoff is 1 mutez payable reward
        if self.delegator_pays_xfer_fee:
            self.default_zero_threshold += self.default_fee

        logger.info(
            "Default transfer fee is {:<,d} mutez for tz addresses and is paid by {}.".format(
                self.default_fee,
                "Delegator" if self.delegator_pays_xfer_fee else "Delegate",
            )
        )
        logger.info(
            "Reactivation fee (burn fee) for tz addresses is {:<,d} mutez and is paid by {}.".format(
                int(TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["BURN_FEE"]),
                "Delegator" if self.delegator_pays_ra_fee else "Delegate",
            )
        )
        logger.info(
            "Minimum payment amount is {:<,d} mutez for tz addresses.".format(
                self.default_zero_threshold
            )
        )
        logger.info(
            "Transfer fees and storage burn fees for kt accounts are determined by simulation."
        )

        # If pymnt_addr has a length of 36 and starts with tz then it is a public key, else it is an alias or kt
        AddressValidator().tz_validate(self.pymnt_addr)
        self.source = self.pymnt_addr
        logger.debug("Payment address is {}".format(self.source))

        self.comm_payment_head = COMM_PAYMENT_HEAD
        self.comm_head = COMM_HEAD
        self.comm_counter = COMM_COUNTER.format(self.source)
        self.comm_runops = COMM_RUNOPS
        self.comm_forge = COMM_FORGE
        self.comm_preapply = COMM_PREAPPLY
        self.comm_inject = COMM_INJECT
        self.comm_wait = COMM_WAIT

    def pay(self, payment_items_in, dry_run=None):
        # initialize the result list with already paid items
        logger.info("{} payment items to process".format(len(payment_items_in)))
        payment_logs = init_payment_logs(payment_items_in)

        unprocessed_payment_items = [
            pi for pi in payment_items_in if not pi.paid.is_processed()
        ]

        # all unprocessed_payment_items are important (non-trivial)
        # gather up all unprocessed_payment_items that are greater than, or equal to the zero_threshold
        # zero_threshold is either 1 mutez or the txn fee if delegator is not paying it, and burn fee
        payment_items = []
        estimated_sum_burn_fees = 0
        estimated_sum_xfer_fees = 0
        for payment_item in unprocessed_payment_items:
            # Reinitialize status for items fetched from failed payment files
            if payment_item.paid.is_fail():
                payment_item.paid = PaymentStatus.UNDEFINED
            # Check if payment item was skipped due to any of the phase calculations.
            # Add any items which are marked as skipped to the returning array so that they are logged to reports.
            if not payment_item.payable:
                logger.info(
                    "Skipping payout to {:s} of {:<,d} mutez, reason: {:s}".format(
                        payment_item.address,
                        payment_item.adjusted_amount,
                        payment_item.desc,
                    )
                )
                payment_logs.append(payment_item)
                continue

            tmp_zt = self.default_zero_threshold
            tmp_xfer = self.default_fee
            tmp_burn = 0
            # Treat kt accounts like normal tz1 addresses and sort them out later on
            if payment_item.needs_activation:
                # Need to apply this fee to only those which need reactivation
                tmp_xfer += max(
                    int(
                        TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["FEE"]
                        - TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"]
                    ),
                    0,
                )
                tmp_burn += TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["BURN_FEE"]
                if self.delegator_pays_xfer_fee:
                    tmp_zt += max(
                        int(
                            TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["FEE"]
                            - TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"]
                        ),
                        0,
                    )

                if self.delegator_pays_ra_fee:
                    tmp_zt += int(TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["BURN_FEE"])

            # If payout total greater than, or equal to zero threshold, append payout record to master array
            if payment_item.adjusted_amount >= tmp_zt:
                # Check here if payout amount is greater than, or equal to new zero threshold with reactivation fee added.
                # If so, add burn fee to global total. If not, payout will not get appended to list and therefor burn fee should not be added to global total.
                estimated_sum_burn_fees += tmp_burn
                estimated_sum_xfer_fees += tmp_xfer
                payment_items.append(payment_item)
            else:
                payment_item.paid = PaymentStatus.DONE
                payment_item.desc += "Payment amount < ZERO_THRESHOLD. "
                payment_logs.append(payment_item)
                logger.debug(
                    "Skipping payout to {:s} of {:<,d} mutez, reason: payout below minimum of {:<,d} mutez".format(
                        payment_item.address, payment_item.adjusted_amount, tmp_zt
                    )
                )

        if len(payment_items) == 0:
            logger.info("No payment items found, returning...")
            return payment_logs, 0, 0, 0, None

        # This is an estimate to predict if the payment account holds enough funds to payout this cycle and the number of future cycles
        estimated_amount_to_pay = calculate_estimated_amount_to_pay(
            payment_items,
            estimated_sum_xfer_fees,
            estimated_sum_burn_fees,
            self.delegator_pays_xfer_fee,
            self.delegator_pays_ra_fee,
        )

        # split payments into lists of MAX_TX_PER_BLOCK or less size
        # [list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,...]

        payment_items_chunks = sort_and_chunk_payment_items(payment_items)

        payment_address_balance = int(self.get_payment_address_balance())

        logger.info(
            "Total estimated amount to pay out is {:<,d} mutez.".format(
                estimated_amount_to_pay
            )
        )
        logger.info(
            "{} payments will be done in {} batches".format(
                len(payment_items), len(payment_items_chunks)
            )
        )

        if payment_address_balance is not None:
            logger.info(
                "Current balance in payout address is {:<,d} mutez.".format(
                    payment_address_balance
                )
            )

            number_future_payable_cycles = calculate_future_payable_cycles(
                payment_address_balance, estimated_amount_to_pay
            )

            if number_future_payable_cycles < 0:
                for payment_item in payment_items:
                    payment_item.paid = PaymentStatus.FAIL
                    payment_item.desc += "Insufficient funds. "

                subject = "FAILED Payouts - Insufficient Funds"
                message = (
                    "Payment attempt failed because of insufficient funds in the payout address. "
                    "The current balance of {:<,d} mutez is insufficient to pay for cycle rewards of {:<,d} mutez.".format(
                        payment_address_balance,
                        estimated_amount_to_pay,
                    )
                )

                # Output to CLI, send notification using plugins
                logger.error(message)
                self.plugins_manager.send_admin_notification(subject, message)

                payment_logs.extend(payment_items)
                # Exit early since nothing can be paid
                return payment_logs, 0, 0, 0, ExitCode.INSUFFICIENT_FUNDS

            elif number_future_payable_cycles < 1:
                subject = "WARNING Payouts - Low Payment Address Funds"
                message = (
                    "The payout address will soon run out of funds. The current balance, {:<,d} mutez, "
                    "might not be sufficient for the next cycle".format(
                        payment_address_balance
                    )
                )

                logger.warning(message)
                self.plugins_manager.send_admin_notification(subject, message)

            else:
                logger.info(
                    "The payout account balance is expected to last for the next {:d} cycle(s)".format(
                        number_future_payable_cycles
                    )
                )

        total_attempts = 0
        op_counter = OpCounter()

        # Calculate actual payment amount after previous estimate for each chunk in chunks iteratively
        amount_to_pay = delegator_transaction_fees = delegate_transaction_fees = 0

        for i_batch, payment_items_chunk in enumerate(payment_items_chunks):
            logger.info("Payment of batch {} started".format(i_batch + 1))
            status = PaymentStatus.UNDEFINED
            attempt, status = self.pay_single_batch(
                payment_items_chunk, dry_run=dry_run, op_counter=op_counter
            )

            logger.info(
                "Payment of batch {} {} in {} attempt(s)".format(
                    i_batch + 1, "failed" if status.is_fail() else "succeeded", attempt
                )
            )

            for payment_item in payment_items_chunk:
                if (
                    payment_item.paid.is_paid()
                    or payment_item.paid.is_injected()
                    or payment_item.paid.is_done()
                ):
                    amount_to_pay += payment_item.adjusted_amount
                    delegator_transaction_fees += payment_item.delegator_transaction_fee
                    delegate_transaction_fees += payment_item.delegate_transaction_fee

            payment_logs.extend(payment_items_chunk)
            total_attempts += attempt

        amount_to_pay = (
            amount_to_pay - delegator_transaction_fees + delegate_transaction_fees
        )

        logger.info(
            "Total amount payed out is {:<,d} mutez in {} attempts and {} batches.".format(
                amount_to_pay, total_attempts, len(payment_items_chunks)
            )
        )

        return (
            payment_logs,
            total_attempts,
            amount_to_pay,
            number_future_payable_cycles,
            None,
        )

    def pay_single_batch(self, payment_items, op_counter, dry_run=None):
        max_try = MAX_BATCH_PAYMENT_ATTEMPTS
        status = PaymentStatus.UNDEFINED
        error_message = ""
        operation_hash = None
        attempt_count = 0

        # for failed operations, trying after some time should be OK
        for attempt in range(max_try):
            try:
                status, operation_hash, error_message = self.attempt_single_batch(
                    payment_items, op_counter, dry_run=dry_run
                )
            except Exception:
                logger.error(
                    "Batch payment attempt {}/{} for current batch failed with error".format(
                        attempt + 1, max_try
                    ),
                    exc_info=True,
                )

            if dry_run or status.is_fail():
                op_counter.rollback()
            else:
                op_counter.commit()

            # we do not want to preserve counter anymore
            # force re-read of counter at every try
            op_counter.set(None)

            attempt_count += 1

            logger.debug("Payment attempt {}/{} failed".format(attempt + 1, max_try))

            # if not fail, do not try anymore
            if not status.is_fail():
                break

            # But do not wait after last attempt
            if attempt < max_try - 1:
                block_time = self.network_config["MINIMAL_BLOCK_DELAY"]
                wait_random(block_time)

        for payment_item in payment_items:
            if payment_item.paid.is_undefined():
                payment_item.paid = status
                payment_item.hash = operation_hash
                payment_item.desc += error_message

        return attempt_count, status

    def simulate_single_operation(self, payment_item, pymnt_amnt, branch, chain_id):
        # Initial gas, storage and transaction limits
        gas_limit = HARD_GAS_LIMIT_PER_OPERATION
        storage_limit = HARD_STORAGE_LIMIT_PER_OPERATION
        tx_fee = calculate_tx_fee(self.default_fee)
        content = (
            CONTENT.replace("%SOURCE%", str(self.source))
            .replace("%DESTINATION%", str(payment_item.paymentaddress))
            .replace("%AMOUNT%", str(pymnt_amnt))
            .replace("%COUNTER%", str(self.base_counter + 1))
            .replace("%fee%", str(tx_fee))
            .replace("%gas_limit%", str(gas_limit))
            .replace("%storage_limit%", str(storage_limit))
        )

        runops_json = build_runops_json_params(branch, content, chain_id)
        status, run_ops_parsed = self.clnt_mngr.request_url_post(
            cmd=self.comm_runops, json_params=runops_json
        )
        if status != HTTPStatus.OK:
            logger.error("Error in run_operation")
            return PaymentStatus.FAIL, []
        op = run_ops_parsed["contents"][0]

        status = op["metadata"]["operation_result"]["status"]
        if status == "applied":
            # Calculate actual consumed gas amount
            consumed_gas = (
                calculate_consumed_gas(
                    consumed_milligas=op["metadata"]["operation_result"][
                        "consumed_milligas"
                    ],
                    metadata=op["metadata"],
                )
                + 100
            )
            # Calculate actual used storage
            consumed_storage = calculate_consumed_storage(op["metadata"])
        else:
            return log_and_fail(op["metadata"]["operation_result"])

        # Calculate needed fee for the transaction, for that we need the size of the forged transaction in bytes
        tx_fee += math.ceil(consumed_gas * MUTEZ_PER_GAS_UNIT)
        content = (
            CONTENT.replace("%SOURCE%", str(self.source))
            .replace("%DESTINATION%", str(payment_item.paymentaddress))
            .replace("%AMOUNT%", str(pymnt_amnt))
            .replace("%COUNTER%", str(self.base_counter + 1))
            .replace("%fee%", str(tx_fee))
            .replace("%gas_limit%", str(consumed_gas))
            .replace("%storage_limit%", str(consumed_storage))
        )
        forge_json = FORGE_JSON.replace("%BRANCH%", branch).replace(
            "%CONTENT%", content
        )
        status, bytes = self.clnt_mngr.request_url_post(self.comm_forge, forge_json)
        if status != HTTPStatus.OK:
            logger.error("Error in forge operation")
            return PaymentStatus.FAIL, []
        # Now that we have the size of the transaction, compute the required fee
        size = SIGNATURE_BYTES_SIZE + len(bytes) / 2
        required_fee = calculate_required_fee(consumed_gas, size)
        # Check if the pre-computed tx_fee is higher or equal than the minimal required fee
        while tx_fee < required_fee:
            # Re-adjust according to the new fee
            tx_fee = required_fee
            tx = json.loads(content)
            tx["fee"] = str(tx_fee)
            content = json.dumps(tx)
            forge_json = FORGE_JSON.replace("%BRANCH%", branch).replace(
                "%CONTENT%", content
            )
            status, bytes = self.clnt_mngr.request_url_post(self.comm_forge, forge_json)
            if status != HTTPStatus.OK:
                logger.error("Error in forge operation")
                return PaymentStatus.FAIL, []

            # Compute the new required fee. It is possible that the size of the transaction in bytes is now higher
            # because of the increase in the fee of the first transaction
            size = SIGNATURE_BYTES_SIZE + len(bytes) / 2
            required_fee = calculate_required_fee(consumed_gas, size)
        simulation_results = consumed_gas, tx_fee, consumed_storage
        return PaymentStatus.DONE, simulation_results

    def attempt_single_batch(self, payment_items, op_counter, dry_run=None):
        if not op_counter.get():
            status, counter = self.clnt_mngr.request_url(self.comm_counter)
            if status != HTTPStatus.OK:
                raise Exception(
                    "Received response code {} for request '{}'".format(
                        status, self.comm_counter
                    )
                )
            counter = int(counter)
            self.base_counter = int(counter)
            op_counter.set(self.base_counter)
        _, head = self.clnt_mngr.request_url(self.comm_payment_head)
        branch = head["hash"]
        chain_id = head["chain_id"]
        protocol = head["metadata"]["protocol"]

        logger.debug(
            "head: branch {} counter {} protocol {}".format(
                branch, op_counter.get(), protocol
            )
        )

        content_list = []

        total_gas = total_tx_fees = total_burn_fees = 0

        for payment_item in payment_items:
            pymnt_amnt = payment_item.adjusted_amount  # expected in micro tez

            # Get initial default values for storage, gas and fees
            # These default values are used for non-empty tz1 accounts transactions
            storage_limit, gas_limit, tx_fee, burn_fee = (
                self.default_storage_limit,
                self.default_gas_limit,
                self.default_fee,
                0,
            )

            # TRD extension for non scriptless contract accounts
            if payment_item.paymentaddress.startswith("KT"):
                try:
                    (
                        simulation_status,
                        simulation_results,
                    ) = self.simulate_single_operation(
                        payment_item, pymnt_amnt, branch, chain_id
                    )

                except Exception as e:
                    logger.info(
                        "Payment to {} script could not be processed. Payment simulation failed with error: {}: {} ".format(
                            payment_item.paymentaddress, type(e).__name__, str(e)
                        )
                    )
                    payment_item.paid = PaymentStatus.FAIL
                    payment_item.desc += "Payment simulation encountered an error while executing. Marking payment as failed. "
                    continue

                if simulation_status.is_fail():
                    logger.info(
                        "Payment to {} script could not be processed. Possible reason: liquidated contract. Avoiding. Think about redirecting the payout to the owner address using the maps rules. Please refer to the TRD documentation or to one of the TRD maintainers.".format(
                            payment_item.paymentaddress
                        )
                    )
                    payment_item.paid = PaymentStatus.AVOIDED
                    payment_item.desc += "Investigate on https://tzkt.io - Liquidated oven or no default entry point. Use rules map for payment redirect. "
                    continue

                gas_limit, tx_fee, storage_limit = simulation_results
                burn_fee = COST_PER_BYTE * storage_limit

                if KT1_FEE_SAFETY_CHECK:
                    total_fee = tx_fee + burn_fee
                    if total_fee > FEE_LIMIT_CONTRACTS:
                        logger.info(
                            "Payment to {:s} script requires higher fees than allowed maximum. Skipping. Needed fee: {:<,d} mutez, max fee: {:<,d} mutez. Either configure a higher fee or redirect to the owner address using the maps rules. Refer to the TRD documentation.".format(
                                payment_item.paymentaddress,
                                total_fee,
                                FEE_LIMIT_CONTRACTS,
                            )
                        )
                        payment_item.paid = PaymentStatus.AVOIDED
                        payment_item.desc += "Kt safety check: Transaction fees higher then allowed maximum: {:<,d} mutez. ".format(
                            FEE_LIMIT_CONTRACTS,
                        )
                        continue

                    if (pymnt_amnt - total_fee) < ZERO_THRESHOLD:
                        logger.info(
                            "Payment to {:s} requires fees of {:<,d} mutez higher than payment amount of {:<,d} mutez. "
                            "Payment avoided due KT1_FEE_SAFETY_CHECK set to True.".format(
                                payment_item.paymentaddress,
                                total_fee,
                                pymnt_amnt,
                            )
                        )
                        payment_item.paid = PaymentStatus.AVOIDED
                        payment_item.desc += "Kt safety check: Burn + transaction fees higher then payment amount. "
                        continue

            else:
                # An implicit tz1 account
                if payment_item.needs_activation:
                    tx_fee += max(
                        int(
                            TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["FEE"]
                            - TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["FEE"]
                        ),
                        0,
                    )
                    # same in Ithaca for allocated and non-allocated
                    gas_limit += max(
                        int(
                            TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["GAS_LIMIT"]
                            - TX_FEES["TZ1_TO_ALLOCATED_TZ1"]["GAS_LIMIT"]
                        ),
                        0,
                    )

                    storage_limit += int(
                        TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["STORAGE_LIMIT"]
                    )
                    # burn_fee = COST_PER_BYTE * RA_STORAGE
                    burn_fee = int(TX_FEES["TZ1_TO_NON_ALLOCATED_TZ1"]["BURN_FEE"])

                    payment_item.desc += "Empty account needed reactivation. "

            message = "Payment to {} requires {:<,d} gas * {:.2f} mutez-per-gas + {:<,d} mutez burn fee\n ".format(
                payment_item.paymentaddress,
                gas_limit,
                MUTEZ_PER_GAS_UNIT,
                burn_fee,
            )
            if burn_fee > 0:
                if self.delegator_pays_ra_fee:
                    # Subtract burn fee from the payment amount
                    orig_pymnt_amnt = pymnt_amnt
                    pymnt_amnt = max(pymnt_amnt - burn_fee, 0)
                    payment_item.delegator_transaction_fee += burn_fee

                    message += "Payment reduced from {:<,d} mutez to {:<,d} mutez because Delegator pays burn fees. ".format(
                        orig_pymnt_amnt,
                        pymnt_amnt,
                    )
                else:
                    payment_item.delegate_transaction_fee += burn_fee

            # Subtract transaction's fee from the payment amount if delegator has to pay for it
            if self.delegator_pays_xfer_fee:
                # Subtract tx fee from the payment amount
                orig_pymnt_amnt = pymnt_amnt
                pymnt_amnt = max(pymnt_amnt - tx_fee, 0)
                payment_item.delegator_transaction_fee += tx_fee

                message += "Payment reduced from {:<,d} mutez to {:<,d} mutez because Delegator pays transaction fees. ".format(
                    orig_pymnt_amnt,
                    pymnt_amnt,
                )
            else:
                payment_item.delegate_transaction_fee += tx_fee

            # Resume main logic

            # if pymnt_amnt becomes < ZERO_THRESHOLD, don't pay

            if pymnt_amnt < ZERO_THRESHOLD:
                payment_item.paid = PaymentStatus.DONE
                payment_item.delegator_transaction_fee = 0
                payment_item.delegate_transaction_fee = 0
                payment_item.desc += (
                    "Payment amount < ZERO_THRESHOLD after substracting fees. "
                )

                message += "Payment to {:s} became < {:<,d} mutez after deducting fees. Skipping.".format(
                    payment_item.paymentaddress, ZERO_THRESHOLD
                )

                logger.info(message)
                continue
            else:
                logger.debug(message)

            op_counter.inc()

            total_gas += int(gas_limit)
            total_burn_fees += int(burn_fee)
            total_tx_fees += int(tx_fee)

            content = (
                CONTENT.replace("%SOURCE%", self.source)
                .replace("%DESTINATION%", payment_item.paymentaddress)
                .replace("%AMOUNT%", str(pymnt_amnt))
                .replace("%COUNTER%", str(op_counter.get()))
                .replace("%fee%", str(tx_fee))
                .replace("%gas_limit%", str(gas_limit))
                .replace("%storage_limit%", str(storage_limit))
            )

            content_list.append(content)

            verbose_logger.info("Payment content: {}".format(content))
        if len(content_list) == 0:
            return PaymentStatus.DONE, None, ""
        contents_string = ",".join(content_list)

        # run the operations for simulation results
        logger.debug("Running {} operations".format(len(content_list)))
        runops_json = RUNOPS_JSON.replace("%BRANCH%", branch).replace(
            "%CONTENT%", contents_string
        )
        runops_json = JSON_WRAP.replace("%JSON%", runops_json).replace(
            "%chain_id%", chain_id
        )

        status, run_ops_parsed = self.clnt_mngr.request_url_post(
            self.comm_runops, runops_json
        )
        if status != HTTPStatus.OK:
            error_message = "Error in run_operation"
            logger.error(error_message)
            return PaymentStatus.FAIL, None, error_message

        # Check each contents object for failure
        for op in run_ops_parsed["contents"]:
            # https://docs.python.org/3/glossary.html#term-eafp
            try:
                op_status = op["metadata"]["operation_result"]["status"]
                if op_status == "failed":
                    op_error = op["metadata"]["operation_result"]["errors"][0]["id"]
                    error_message = "Error while validating operation - Status: {}, Message: {}".format(
                        op_status, op_error
                    )
                    logger.error(error_message)
                    return PaymentStatus.FAIL, None, error_message
            except KeyError:
                logger.debug(
                    "Unable to find metadata->operation_result->{status,errors} in run_ops response"
                )

        # forge the operations
        logger.debug("Forging {} operations".format(len(content_list)))
        forge_json = FORGE_JSON.replace("%BRANCH%", branch).replace(
            "%CONTENT%", contents_string
        )
        status, bytes = self.clnt_mngr.request_url_post(self.comm_forge, forge_json)
        if status != HTTPStatus.OK:
            error_message = "Error in forge operation"
            logger.error(error_message)
            return PaymentStatus.FAIL, None, error_message

        # Re-compute minimal required fee by the batch transaction and re-adjust the fee if necessary
        size = SIGNATURE_BYTES_SIZE + len(bytes) / 2
        required_fee = math.ceil(
            MINIMUM_FEE_MUTEZ + MUTEZ_PER_GAS_UNIT * total_gas + MUTEZ_PER_BYTE * size
        )
        logger.info(
            f"minimal required fee is {required_fee}, current used fee is {total_tx_fees}"
        )
        # TODO: This should be a function to be more modular as it is called twice
        # If all fees are computed correctly above, the condition of this loop should not be True
        # It is still recommended to leave this block here in order to double-check that all fee calculations
        # were verified and that in the worst case any tiny differences in fee computations are adjusted
        while total_tx_fees < required_fee:
            # The difference in fees will be added to the fee of the first transaction
            # This works because the Tezos blockchain is interested in the sum of all fees in a batch transaction
            # and not in the individual fees of each transaction
            difference_fees = math.ceil(required_fee - total_tx_fees)
            first_tx = json.loads(content_list[0])
            first_tx["fee"] = str(int(first_tx["fee"]) + difference_fees)
            # We do not want to adjust the content (payment amount) anymore and let the delegate pay this fee
            # TODO: Log info in description?
            payment_items[0].delegate_transaction_fee += difference_fees

            # Re-adjust the contents according to the new fee
            total_tx_fees = required_fee
            content_list[0] = json.dumps(first_tx)
            contents_string = ",".join(content_list)
            forge_json = FORGE_JSON.replace("%BRANCH%", branch).replace(
                "%CONTENT%", contents_string
            )
            status, bytes = self.clnt_mngr.request_url_post(self.comm_forge, forge_json)
            if status != HTTPStatus.OK:
                error_message = "Error in forge operation"
                logger.error(error_message)
                return PaymentStatus.FAIL, None, error_message

            # Compute the new required fee. It is possible that the size of the transaction in bytes is now higher
            # because of the increase in the fee of the first transaction
            size = SIGNATURE_BYTES_SIZE + len(bytes) / 2
            required_fee = math.ceil(
                MINIMUM_FEE_MUTEZ
                + MUTEZ_PER_GAS_UNIT * total_gas
                + MUTEZ_PER_BYTE * size
            )
            logger.info(
                f"minimal required fee is {required_fee}, current used fee is {total_tx_fees}"
            )

        # Sign the batch transaction
        signed_bytes = self.clnt_mngr.sign(bytes, self.source)

        # pre-apply operations
        logger.debug("Preapplying the operations")
        preapply_json = (
            PREAPPLY_JSON.replace("%BRANCH%", branch)
            .replace("%CONTENT%", contents_string)
            .replace("%PROTOCOL%", protocol)
            .replace("%SIGNATURE%", signed_bytes)
        )

        # if verbose: print("--> preapply_command_str is |{}|".format(preapply_command_str))

        status, preapply_command_response = self.clnt_mngr.request_url_post(
            self.comm_preapply, preapply_json
        )
        if status != HTTPStatus.OK:
            error_message = "Error in preapply operation"
            logger.error(error_message)
            return PaymentStatus.FAIL, None, error_message

        # if dry_run, skip injection
        if dry_run:
            return PaymentStatus.DONE, None, ""

        # inject the operations
        logger.debug("Injecting {} operations".format(len(content_list)))
        decoded = base58.b58decode(signed_bytes).hex()

        if signed_bytes.startswith("edsig"):  # edsig signature
            decoded_edsig_signature = decoded[10:][
                :-8
            ]  # first 5 bytes edsig, last 4 bytes checksum
            decoded_signature = decoded_edsig_signature
        elif signed_bytes.startswith("sig"):  # generic signature
            decoded_sig_signature = decoded[6:][
                :-8
            ]  # first 3 bytes sig, last 4 bytes checksum
            decoded_signature = decoded_sig_signature
        elif signed_bytes.startswith("p2sig"):
            decoded_sig_signature = decoded[8:][
                :-8
            ]  # first 4 bytes sig, last 4 bytes checksum
            decoded_signature = decoded_sig_signature
        else:
            raise Exception(
                "Signature '{}' is not in expected format".format(signed_bytes)
            )

        if len(decoded_signature) != 128:  # must be 64 bytes
            logger.warn(
                "Signature length must be 128 but it is {}. Signature is '{}'".format(
                    len(signed_bytes), signed_bytes
                )
            )

        signed_operation_bytes = bytes + decoded_signature

        _, head = self.clnt_mngr.request_url(self.comm_head)
        last_level_before_injection = head["header"]["level"]

        status, operation_hash = self.clnt_mngr.request_url_post(
            self.comm_inject, json.dumps(signed_operation_bytes)
        )
        if status != HTTPStatus.OK:
            error_message = "Error in inject operation"
            logger.error(error_message)
            return PaymentStatus.FAIL, None, error_message

        logger.info("Operation hash is {}".format(operation_hash))

        # wait for inclusion
        timeout = (
            MAX_BLOCKS_TO_CHECK_AFTER_INJECTION
            * MAX_NUM_TRIALS_PER_BLOCK
            * self.network_config["MINIMAL_BLOCK_DELAY"]
        )
        logger.info(
            "Waiting for operation {} to be included... Please do not interrupt the process! (Timeout is around {} minutes)".format(
                operation_hash, timeout
            )
        )
        for i in range(
            last_level_before_injection + 1,
            last_level_before_injection + 1 + MAX_BLOCKS_TO_CHECK_AFTER_INJECTION,
        ):
            cmd = self.comm_wait.replace("%BLOCK_HASH%", str(i))
            status = -1
            list_op_hash = []
            trial_i = 0
            while status != HTTPStatus.OK and (trial_i < MAX_NUM_TRIALS_PER_BLOCK):
                sleep(self.network_config["MINIMAL_BLOCK_DELAY"])
                status, list_op_hash = self.clnt_mngr.request_url(cmd)
                trial_i += 1
            if status != HTTPStatus.OK:
                logger.warning(
                    "Level {} could not be queried about operation hashes".format(i)
                )
                break
            for op_hashes in list_op_hash:
                if operation_hash in op_hashes:
                    logger.info("Operation {} is included".format(operation_hash))
                    return PaymentStatus.PAID, operation_hash, ""
            logger.debug(
                "Operation {} is not included at level {}".format(operation_hash, i)
            )
        error_message = (
            "Investigate on https://tzkt.io - Operation {} wait is timed out.".format(
                operation_hash
            )
        )
        logger.warning(error_message)
        return PaymentStatus.INJECTED, operation_hash, error_message

    def get_payment_address_balance(self):
        get_current_balance_request = COMM_DELEGATE_BALANCE.format("head", self.source)
        status, payment_address_balance = self.clnt_mngr.request_url(
            get_current_balance_request
        )

        if status != HTTPStatus.OK:
            logger.warning(
                "Balance request failed! Response code {} is received for request '{}'. See verbose logs for more detail.".format(
                    status, get_current_balance_request
                )
            )
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

    @property
    def counter(self):
        return self.__counter
