import base58

from BussinessConfiguration import BAKING_ADDRESS
from log_config import main_logger
from util.client_utils import client_list_known_contracts, sign
from util.rpc_utils import send_request, parse_response

logger = main_logger

COMM_HASH = "{} rpc get http://{}/chains/main/blocks/head/hash"
COMM_PROT = "{} rpc get http://{}/protocols"
COMM_COUNTER = "{} rpc get http://{}/chains/main/blocks/head/context/contracts/{}/counter"
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"0","counter":"%COUNTER%","gas_limit":"4000000","storage_limit":"600000","amount":"%AMOUNT%"}'
FORGE_JSON = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
PREAPPLY_JSON = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'
COMM_FORGE = "{} rpc post http://%NODE%/chains/main/blocks/head/helpers/forge/operations with '%JSON%'"
COMM_PREAPPLY = "{} rpc post http://%NODE%/chains/main/blocks/head/helpers/preapply/operations with '%JSON%'"
COMM_INJECT = "{} rpc post http://%NODE%/injection/operation with '\"%OPERATION_HASH%\"'"


class BatchPayer():
    def __init__(self, node_url, client_path, key_name):
        super(BatchPayer, self).__init__()
        self.key_name = key_name
        self.node_url = node_url
        self.client_path = client_path

        self.comm_branch = COMM_HASH.format(self.client_path, self.node_url)
        self.comm_protocol = COMM_PROT.format(self.client_path, self.node_url)
        self.comm_counter = COMM_COUNTER.format(self.client_path, self.node_url, BAKING_ADDRESS)
        self.comm_forge = COMM_FORGE.format(self.client_path).replace("%NODE%", self.node_url)
        self.comm_preapply = COMM_PREAPPLY.format(self.client_path).replace("%NODE%", self.node_url)
        self.comm_inject = COMM_INJECT.format(self.client_path).replace("%NODE%", self.node_url)

        self.known_contracts = client_list_known_contracts(self.client_path)
        self.source = self.key_name if self.key_name.startswith("KT") or self.key_name.startswith("tz") else \
            self.known_contracts[self.key_name]

    def pay(self, payment_items):
        counter = parse_response(send_request(self.comm_counter))
        counter = int(counter)

        protocol = "ProtoALphaALphaALphaALphaALphaALphaALphaALphaDdp3zK"
        branch = parse_response(send_request(self.comm_branch))

        content_list = []
        payment_items = payment_items * 2
        for payment_item in payment_items:
            pymnt_addr = payment_item["address"]
            pymnt_amnt = payment_item["payment"]
            pymnt_amnt = int(pymnt_amnt * 1e6)  # expects in micro tezos
            counter = counter + 1
            content = CONTENT.replace("%SOURCE%", self.source).replace("%DESTINATION%", pymnt_addr) \
                .replace("%AMOUNT%", str(pymnt_amnt)).replace("%COUNTER%", str(counter))
            content_list.append(content)

        contents_string = ",".join(content_list)

        forge_json = FORGE_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string)
        forge_command_str = self.comm_forge.replace("%JSON%", forge_json)
        print("forge_command_str is |{}|".format(forge_command_str))
        forge_command_response = send_request(forge_command_str)
        if "Error:" in forge_command_response or "Unexpected server answer" in forge_command_response:
            logger.error("Error '{}'".format(forge_command_response))
            return False

        bytes = parse_response(forge_command_response)
        signed_bytes = sign(self.client_path, bytes, self.key_name)

        preapply_json = PREAPPLY_JSON.replace('%BRANCH%', branch).replace("%CONTENT%", contents_string).replace("%PROTOCOL%",protocol).replace("%SIGNATURE%",signed_bytes)
        preapply_command_str = self.comm_preapply.replace("%JSON%", preapply_json)
        print("preapply_command_str is |{}|".format(preapply_command_str))
        preapply_command_response = send_request(preapply_command_str)
        if "Error:" in preapply_command_response or "Unexpected server answer" in preapply_command_response:
            logger.error("Error '{}'".format(preapply_command_response))
            return False

        # not necessary
        #preapplied = parse_response(preapply_command_response)

        decoded = base58.b58decode(signed_bytes).hex()
        decoded_edsig_signature = decoded.replace("09f5cd8612", "")[:-8]
        signed_operation_bytes = bytes + decoded_edsig_signature
        inject_command_str = self.comm_inject.replace("%OPERATION_HASH%", signed_operation_bytes)
        inject_command_response = send_request(inject_command_str)
        operation_hash = parse_response(inject_command_response)

        logger.debug("Operation hash is {}".format(operation_hash))

        return True


if __name__ == '__main__':
    payer = BatchPayer("127.0.0.1:8273", "~/zeronet.sh client", "mybaker")
