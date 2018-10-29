## choose the right client path

# regular client
# CLIENT_PATH = "~/tezos/tezos-client"

# if docker images are used, %network% will be replaced by mainnet, zeronet, alphanet values
CLIENT_PATH = "~/%network%.sh client"

# transfer command
COMM_TRANSFER = CLIENT_PATH + " transfer {0:f} from {} to {} --fee 0"
