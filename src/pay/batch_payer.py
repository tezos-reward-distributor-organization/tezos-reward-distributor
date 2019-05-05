import configparser
import base58
import os

from log_config import main_logger
from util.client_utils import check_response
from util.rpc_utils import parse_json_response
from random import randint
from time import sleep

logger = main_logger

MAX_TX_PER_BLOCK = 285
PKH_LENGHT = 36
CONFIRMATIONS = 1

COMM_HEAD = " rpc get http://{}/chains/main/blocks/head"
COMM_COUNTER = " rpc get http://{}/chains/main/blocks/head/context/contracts/{}/counter"
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"%fee%","counter":"%COUNTER%","gas_limit": "%gas_limit%", "storage_limit": "%storage_limit%","amount":"%AMOUNT%"}'
FORGE_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
RUNOPS_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%], "signature":"edsigtXomBKi5CTRf5cjATJWSyaRvhfYNHqSUGrn4SdbYRcGwQrUGjzEfQDTuqHhuA8b2d8NarZjz8TRf65WkpQmo423BtomS8Q"}'
PREAPPLY_JSON = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'
COMM_FORGE = " rpc post http://%NODE%/chains/main/blocks/head/helpers/forge/operations with '%JSON%'"
COMM_RUNOPS = " rpc post http://%NODE%/chains/main/blocks/head/helpers/scripts/run_operation with '%JSON%'"
COMM_PREAPPLY = " rpc post http://%NODE%/chains/main/blocks/head/helpers/preapply/operations with '%JSON%'"
COMM_INJECT = " %LOG% rpc post http://%NODE%/injection/operation with '\"%OPERATION_HASH%\"'"
COMM_WAIT = " wait for %OPERATION% to be included --confirmations {}".format(CONFIRMATIONS)

FEE_INI = 'fee.ini'
DUMMY_FEE = 1000


class BatchPayer():
    def __init__(self, node_url, pymnt_addr, wllt_clnt_mngr, delegator_pays_xfer_fee):
        super(BatchPayer, self).__init__()
        self.pymnt_addr = pymnt_addr
        self.node_url = node_url
        self.wllt_clnt_mngr = wllt_clnt_mngr

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

        # initialize the result list with already paid items
        payment_logs = [pi for pi in payment_items_in if pi.paid]

        payment_items = [pi for pi in payment_items_in if not pi.paid]

        if payment_logs:
            for pl in payment_logs:
                logger.info("Reward already paid for cycle %s address %s amount %f tz type %s",
                            pl.cycle, pl.address, pl.payment, pl.type)

        # split payments into lists of MAX_TX_PER_BLOCK or less size
        # [list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,list_of_size_MAX_TX_PER_BLOCK,...]
        payment_items_chunks = [payment_items[i:i + MAX_TX_PER_BLOCK] for i in
                                range(0, len(payment_items), MAX_TX_PER_BLOCK)]

        op_counter = OpCounter()
        logger.debug("Payment will be done in {} batches".format(len(payment_items_chunks)))

        for payment_items_chunk in payment_items_chunks:
            logger.debug("Payment of a batch started")
            payments_log = \
                self.pay_single_batch_wrap(payment_items_chunk, verbose=verbose, dry_run=dry_run, op_counter=op_counter)
            payment_logs.extend(payments_log)

            logger.debug("Payment of a batch is complete")

        return payment_logs

    def pay_single_batch_wrap(self, payment_items, op_counter, verbose=None, dry_run=None):

        max_try = 3
        return_code = False
        operation_hash = ""

        # due to unknown reasons, some times a batch fails to pre-apply
        # trying after some time should be OK
        for attempt in range(max_try):
            return_code, operation_hash = \
                self.pay_single_batch(payment_items, op_counter, verbose, dry_run=dry_run)

            if dry_run or not return_code:
                op_counter.rollback()
            else:
                op_counter.commit()

            # we do not want to preserve counter anymore
            # force re-read of counter at every try
            op_counter.set(None)

            # if successful, do not try anymore
            if return_code:
                break

            logger.debug("Batch payment attempt {} failed".format(attempt))

            # But do not wait after last attempt
            if attempt < max_try - 1:
                self.wait_random()

        for payment_item in payment_items:
            payment_item.paid = return_code
            payment_item.hash = operation_hash

        return payment_items

    def wait_random(self):
        slp_tm = randint(10, 50)
        logger.debug("Wait for {} seconds before trying again".format(slp_tm))
        sleep(slp_tm)

    def pay_single_batch(self, payment_records, op_counter, verbose=None, dry_run=None):

        if not op_counter.get():
            counter = parse_json_response(self.wllt_clnt_mngr.send_request(self.comm_counter))
            counter = int(counter)
            op_counter.set(counter)

        head = parse_json_response(self.wllt_clnt_mngr.send_request(self.comm_head))
        branch = head["hash"]
        protocol = head["metadata"]["protocol"]

        logger.debug("head: branch {} counter {} protocol {}".format(branch, op_counter.get(), protocol))

        content_list = []

        for payment_item in payment_records:
            pymnt_amnt = int(payment_item.payment * 1e6)  # expects in micro tezos

            if self.delegator_pays_xfer_fee:
                pymnt_amnt = max(pymnt_amnt - int(self.default_fee), 0)  # ensure not less than 0

            if pymnt_amnt < 1e-3:  # zero check
                continue

            op_counter.inc()
            content = CONTENT.replace("%SOURCE%", self.source).replace("%DESTINATION%", payment_item.address) \
                .replace("%AMOUNT%", str(pymnt_amnt)).replace("%COUNTER%", str(op_counter.get())) \
                .replace("%fee%", self.default_fee).replace("%gas_limit%", self.gas_limit).replace("%storage_limit%",
                                                                                                   self.storage_limit)
            content_list.append(content)

            logger.info("Payment content: {}".format(content))

        contents_string = ",".join(content_list)

        # run the operations
        logger.debug("Running {} operations".format(len(content_list)))
        runops_json = RUNOPS_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        runops_command_str = self.comm_runops.replace("%JSON%", runops_json)
        if verbose: logger.debug("runops_command_str is |{}|".format(runops_command_str))
        runops_command_response = self.wllt_clnt_mngr.send_request(runops_command_str)
        if not check_response(runops_command_response):
            error_desc = parse_json_response(runops_command_response)
            # for content in runops_command_response["contents"]:
            #    op_result = content["metadata"]["operation_result"]
            #    if op_result["status"] == 'failed':
            #        error_desc = op_result["errors"]
            #        break
            logger.error("Error in run_operation response '{}'".format(error_desc))
            return False, ""

        # forge the operations
        logger.debug("Forging {} operations".format(len(content_list)))
        forge_json = FORGE_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        forge_command_str = self.comm_forge.replace("%JSON%", forge_json)
        if verbose: logger.debug("forge_command_str is |{}|".format(forge_command_str))
        forge_command_response = self.wllt_clnt_mngr.send_request(forge_command_str)
        if not check_response(forge_command_response):
            logger.error("Error in forge response '{}'".format(forge_command_response))
            return False, ""

        # sign the operations
        bytes = parse_json_response(forge_command_response, verbose=verbose)
        signed_bytes = self.wllt_clnt_mngr.sign(bytes, self.manager_alias)

        # pre-apply operations
        logger.debug("Preapplying the operations")
        preapply_json = PREAPPLY_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string).replace(
            "%PROTOCOL%", protocol).replace("%SIGNATURE%", signed_bytes)
        preapply_command_str = self.comm_preapply.replace("%JSON%", preapply_json)

        if verbose: logger.debug("preapply_command_str is |{}|".format(preapply_command_str))
        preapply_command_response = self.wllt_clnt_mngr.send_request(preapply_command_str)
        if not check_response(preapply_command_response):
            logger.error("Error in preapply response '{}'".format(preapply_command_response))
            return False, ""

        # not necessary
        # preapplied = parse_response(preapply_command_response)

        # if dry_run, skip injection
        if dry_run: return True, ""

        # inject the operations
        logger.debug("Injecting {} operations".format(len(content_list)))
        decoded = base58.b58decode(signed_bytes).hex()

        if signed_bytes.startswith("edsig"):  # edsig signature
            decoded_edsig_signature = decoded[10:][:-8]  # first 5 bytes edsig, last 4 bytes checksum
            decoded_signature = decoded_edsig_signature
        elif signed_bytes.startswith("sig"):  # generic signature
            decoded_sig_signature = decoded[6:][:-8]  # first 3 bytes sig, last 4 bytes checksum
            decoded_signature = decoded_sig_signature
        else:
            raise Exception("Signature '{}' is not in expected format".format(signed_bytes))

        if len(decoded_signature) != 128:  # must be 64 bytes
            # raise Exception("Signature length must be 128 but it is {}. Signature is '{}'".format(len(signed_bytes), signed_bytes))
            logger.warn(
                "Signature length must be 128 but it is {}. Signature is '{}'".format(len(signed_bytes), signed_bytes))
            # return False, ""

        signed_operation_bytes = bytes + decoded_signature
        inject_command_str = self.comm_inject.replace("%OPERATION_HASH%", signed_operation_bytes)
        inject_command_str = inject_command_str.replace("%LOG%", "-l" if verbose else "")
        if verbose: logger.debug("inject_command_str is |{}|".format(inject_command_str))
        inject_command_response = self.wllt_clnt_mngr.send_request(inject_command_str)
        if not check_response(inject_command_response):
            logger.error("Error in inject response '{}'".format(inject_command_response))
            return False, ""

        operation_hash = parse_json_response(inject_command_response)
        logger.debug("Operation hash is {}".format(operation_hash))

        # wait for inclusion
        logger.debug("Waiting for operation {} to be included. Please be patient until the block has {} confirmation(s)"
                     .format(operation_hash, CONFIRMATIONS))
        self.wllt_clnt_mngr.send_request(self.comm_wait.replace("%OPERATION%", operation_hash))

        logger.debug("Operation {} is included".format(operation_hash))

        return True, operation_hash


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
