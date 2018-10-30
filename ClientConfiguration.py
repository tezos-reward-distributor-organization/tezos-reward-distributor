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

COMM_COUNTER = CLIENT_PATH + " rpc get http://{}/chains/main/blocks/head/context/contracts/{}/counter".format(NODE_URL,
                                                                                                             BAKING_ADDRESS)
