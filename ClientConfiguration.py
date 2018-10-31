## choose the right client path

# regular client
# CLIENT_PATH = "~/tezos/tezos-client"

# if docker images are used, %network% will be replaced by mainnet, zeronet, alphanet values
from BussinessConfiguration import BAKING_ADDRESS

CLIENT_PATH = "~/%network%.sh client"

NODE_ADDR = "127.0.0.1"
NODE_PORT = "8732"
NODE_URL = NODE_ADDR + ":" + NODE_PORT

# transfer command
COMM_TRANSFER = CLIENT_PATH + " transfer {0:f} from {1} to {2} --fee 0"

COMM_HASH = CLIENT_PATH + " rpc get http://{}/chains/main/blocks/head/hash".format(NODE_URL)
COMM_PROT = CLIENT_PATH + " rpc get http://{}/protocols".format(NODE_URL)

content0 = '{ "kind": "transaction", "amount": "100000", "source": "tz1YZReTLamLhyPLGSALa4TbMhjjgnSi2cqP", "destination": "tz1MWTkFRXA2dwez4RHJWnDWziLpaN6iDTZ9", "storage_limit": "0", "gas_limit": "200", "fee": "0", "counter": "9832" }'
COMM_FORGE = CLIENT_PATH + " rpc post http://" + NODE_URL + "/chains/main/blocks/head/helpers/forge/operations with " + '\'{"contents": [ ' + content0 + ' ], "branch": "BLgHmTatrJ8t449afM8gUgvB2ebbspjV7yfTUKYtgbz9s3DzG1t"}\''
COMM_PREAPPLY = CLIENT_PATH + " rpc post http://" + NODE_URL + "/chains/main/blocks/head/helpers/preapply/operations with " + '\'[{"protocol": "%PROTOCOL%", "signature": "%SIGNATURE%","branch": "%BRANCH%", "contents": [ ' + content0 + ' ]}]\''
COMM_COUNTER = CLIENT_PATH + " rpc get http://{}/chains/main/blocks/head/context/contracts/{}/counter".format(NODE_URL,
                                                                                                              BAKING_ADDRESS)
COMM_SIGN = CLIENT_PATH +" sign bytes 0x03{} for zeronetme2"
