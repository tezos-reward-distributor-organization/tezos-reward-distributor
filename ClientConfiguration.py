## choose the right client path

# regular client
# CLIENT_PATH = "~/tezos/tezos-client"

# if docker images are used, %network% will be replaced by mainnet, zeronet, alphanet values
CLIENT_PATH = "~/%network%.sh client"

NODE_ADDR = "127.0.0.1"
NODE_PORT = "8732"
NODE_URL = NODE_ADDR + ":" + NODE_PORT

SHELL_COMM_DISABLE_DISCLAIMER = "export TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=Y"

# transfer command
COMM_TRANSFER = CLIENT_PATH + " transfer {} from {} to {} --fee 0"

COMM_HASH = CLIENT_PATH + " rpc get http://{}/chains/main/blocks/head/hash".format(NODE_URL)
