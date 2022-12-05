from enum import Enum

# General
VERSION = 11.0
PYTHON_MAJOR = 3
PYTHON_MINOR = 7
LINER = "--------------------------------------------"

# Persistent data directories
BASE_DIR = "~/pymnt"
CONFIG_DIR = "cfg"
SIMULATIONS_DIR = "simulations"
REPORTS_DIR = "reports"
DEFAULT_LOG_FILE = "logs/app.log"
TEMP_TEST_DATA_DIR = "__TEMP_DATA__"
REQUIREMENTS_FILE_PATH = "requirements.txt"

LOCAL_HOST = "127.0.0.1"
EXIT_PAYMENT_TYPE = "exit"
# https://forum.tezosagora.org/t/turning-ithacanet-into-a-permanent-testnet-ghostnet/4614
TESTNET_PREFIX = "ghost"
TESTNET_SUFFIX = "net"
CURRENT_TESTNET = (TESTNET_PREFIX + TESTNET_SUFFIX).upper()


MAX_SEQUENT_CALLS = 256  # to prevent possible endless looping

FIRST_GRANADA_LEVEL = 1589249

TEZOS_RPC_PORT = 8732

SIGNER_PORT = 6732

# Attention: We do not use a lib to join URLs
# Join them like this:
# >>> url = "http://base" + "/append" # look at the "/" of the appending part

# Local URLs
PRIVATE_SIGNER_URL = "http://{}:{}".format(LOCAL_HOST, SIGNER_PORT)
PRIVATE_NODE_URL = "http://{}:{}".format(LOCAL_HOST, TEZOS_RPC_PORT)

# Public RPC
PUBLIC_NODE_URL = {
    "MAINNET": "https://rpc.tzkt.io/mainnet",
    CURRENT_TESTNET: "https://rpc.tzkt.io/{}".format(CURRENT_TESTNET.lower()),
}

# TzStats
TZSTATS_PUBLIC_API_URL = {
    "MAINNET": "https://api.tzstats.com",
    CURRENT_TESTNET: "https://api.{}.tzstats.com".format(TESTNET_PREFIX.lower()),
}

# TzKT
TZKT_PUBLIC_API_URL = {
    "MAINNET": "https://api.tzkt.io/v1",
    CURRENT_TESTNET: "https://api.{}.tzkt.io/v1".format(CURRENT_TESTNET.lower()),
}

# Network Constants
# ------------------------
#
# General:
# Last change with Ithaca protocol
# https://research-development.nomadic-labs.com/announcing-tezos-9th-protocol-upgrade-proposal-ithaca.html
# https://tezos.gitlab.io/ithaca/consensus.html#rewards
# https://tezos.gitlab.io/ithaca/consensus.html#consensus-related-protocol-parameters
#
# Mainnet:
# https://mainnet.smartpy.io/chains/main/blocks/head/context/constants
#
# Testnet:
# https://ghostnet.smartpy.io/chains/main/blocks/head/context/constants
DEFAULT_NETWORK_CONFIG_MAP = {
    "MAINNET": {
        # General
        "NAME": "MAINNET",
        "NB_FREEZE_CYCLE": 5,  # needs deprecation
        "MINIMAL_BLOCK_DELAY": 30,
        "BLOCKS_PER_CYCLE": 8192,
        "BLOCKS_PER_STAKE_SNAPSHOT": 512,
        # Consensus
        "CONSENSUS_COMMITTEE_SIZE": 7000,
        "CONSENSUS_THRESHOLD": 4667,
        "BAKING_REWARD_FIXED_PORTION": 10000000,
        "BAKING_REWARD_BONUS_PER_SLOT": 4286,
        "ENDORSING_REWARD_PER_SLOT": 2857,
        # Fixed baking amount (10)+ bonus (10 in the best case)
        "BLOCK_REWARD": 20000000,
        # endorsing_reward = (1 - baking_reward_ratio) * (1 - bonus_ratio) * total_rewards
        # = (1-1/4)*(1-1/3)*40
        "ENDORSEMENT_REWARDS": 20000000,
    },
    CURRENT_TESTNET: {
        # General
        "NAME": CURRENT_TESTNET,
        "NB_FREEZE_CYCLE": 3,  # needs deprecation
        "MINIMAL_BLOCK_DELAY": 15,
        "BLOCKS_PER_CYCLE": 4096,
        "BLOCKS_PER_STAKE_SNAPSHOT": 256,
        # Consensus
        "CONSENSUS_COMMITTEE_SIZE": 7000,
        "CONSENSUS_THRESHOLD": 4667,
        "BAKING_REWARD_FIXED_PORTION": 5000000,
        "BAKING_REWARD_BONUS_PER_SLOT": 2143,
        "ENDORSING_REWARD_PER_SLOT": 1428,
        #
        "BLOCK_REWARD": 10000000,
        "ENDORSEMENT_REWARDS": 10000000,
    },
}

MUTEZ_PER_TEZ = 1e6

MAXIMUM_ROUNDING_ERROR = 10  # mutez
ALMOST_ZERO = 1e-6
DISK_LIMIT_PERCENTAGE = 0.1
GIGA_BYTE = 1e9
DISK_LIMIT_SIZE = 5 * GIGA_BYTE

BUF_SIZE = 50


class DryRun(str, Enum):
    SIGNER = 'SIGNER'
    NO_SIGNER = 'NO_SIGNER'


class RunMode(Enum):
    FOREVER = 1
    PENDING = 2
    ONETIME = 3
    RETRY_FAILED = 4


class PaymentStatus(Enum):
    """
    PAID: payment successfully made.
    FAIL: Some failures happened in the process.
    DONE: Process completed without payment. E.g. zero amount, dry run...
    INJECTED: Transaction is injected into the node but after waiting for some time it is not added to any block.
    AVOIDED: payment item avoided because of lack of support, incompatibility of contract script,
             contract with no default entry point, too high fees, liquidated contract, etc.
    TRD does not know its fate.
    """

    UNDEFINED = -1
    FAIL = 0
    PAID = 1
    DONE = 2
    INJECTED = 3
    AVOIDED = 4

    def is_fail(self):
        return self.value == 0

    def is_processed(self):
        return self.value > 0

    def __str__(self):
        return self.name


class RewardsType(Enum):
    ACTUAL = "actual"
    IDEAL = "ideal"
    ESTIMATED = "estimated"

    def isEstimated(self):
        return self == RewardsType.ESTIMATED

    def isActual(self):
        return self == RewardsType.ACTUAL

    def isIdeal(self):
        return self == RewardsType.IDEAL

    def __str__(self):
        return self.value
