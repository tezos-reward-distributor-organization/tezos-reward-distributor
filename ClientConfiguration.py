## choose the right client path

# regular client
# CLIENT_PATH = "~/tezos/tezos-client"

# if docker images are used, %network% will be replaced by mainnet, zeronet, alphanet values
import os

from BussinessConfiguration import BAKING_ADDRESS

CLIENT_PATH = os.path.expanduser("~/%network%.sh client")

NODE_ADDR = "127.0.0.1"
NODE_PORT = "8732"
NODE_URL = NODE_ADDR + ":" + NODE_PORT

COMM_COUNTER = CLIENT_PATH + " rpc get http://{}/chains/main/blocks/head/context/contracts/{}/counter".format(NODE_URL, BAKING_ADDRESS)
COMM_SIGN = CLIENT_PATH + " sign bytes 0x03%BYTES% for zeronetme2"

# transfer command
COMM_TRANSFER = CLIENT_PATH + " transfer {0:f} from {1} to {2} --fee 0"

COMM_HASH = CLIENT_PATH + " rpc get http://{}/chains/main/blocks/head/hash".format(NODE_URL)
COMM_PROT = CLIENT_PATH + " rpc get http://{}/protocols".format(NODE_URL)

protocol = 'ProtoALphaALphaALphaALphaALphaALphaALphaALphaDdp3zK'

# content2 = '{"kind":"transaction","source":"tz1YZReTLamLhyPLGSALa4TbMhjjgnSi2cqP","fee":"0","counter":"9836","gas_limit":"4000000","storage_limit":"600000","amount":"100000","destination":"tz1MWTkFRXA2dwez4RHJWnDWziLpaN6iDTZ9"}'
# content22='{"kind":"transaction","source":"tz1YZReTLamLhyPLGSALa4TbMhjjgnSi2cqP","fee":"0","counter":"9836","gas_limit":"200","storage_limit":"0","amount":"100000","destination":"tz1MWTkFRXA2dwez4RHJWnDWziLpaN6iDTZ9"}'
CONTENT = '{"kind":"transaction","source":"%SOURCE%","destination":"%DESTINATION%","fee":"0","counter":"%COUNTER%","gas_limit":"4000000","storage_limit":"600000","amount":"%AMOUNT%"}'
forge_operations = '{"branch": "%BRANCH%","contents":[%CONTENT%]}'
preapply_operations = '[{"protocol":"%PROTOCOL%","branch":"%BRANCH%","contents":[%CONTENT%],"signature":"%SIGNATURE%"}]'

COMM_FORGE = CLIENT_PATH + " rpc post http://%NODE%/chains/main/blocks/head/helpers/forge/operations with '%CONTENT%'".replace("%NODE%",NODE_URL).replace('%CONTENT%',forge_operations)
COMM_PREAPPLY = CLIENT_PATH + " rpc post http://%NODE%/chains/main/blocks/head/helpers/preapply/operations with '%CONTENT%'".replace("%NODE%",NODE_URL).replace('%CONTENT%',preapply_operations)

COMM_INJECT=CLIENT_PATH + " rpc post http://%NODE%/injection/operation with '\"%OPERATION_HASH%\"'".replace("%NODE%",NODE_URL)