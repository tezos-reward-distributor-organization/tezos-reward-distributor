from enum import Enum

EXIT_PAYMENT_TYPE = "exit"

CURRENT_TESTNET = 'FLORENCENET'

# Providers api prefix
# Public RPC
PUBLIC_NODE_URL = {"MAINNET": "https://mainnet-tezos.giganode.io",
                   CURRENT_TESTNET: "https://testnet-tezos.giganode.io"}

# TzStats
TZSTATS_PREFIX_API = {
    'MAINNET': 'https://api.tzstats.com',
    CURRENT_TESTNET: 'https://api.edo2net.tzstats.com'
}

# TzKt
TZKT_API_PREFIX = {
    'MAINNET': 'https://api.tzkt.io/v1',
    CURRENT_TESTNET: 'https://api.{}.tzkt.io/v1'.format(CURRENT_TESTNET)
}


# Network constants
DEFAULT_NETWORK_CONFIG_MAP = {
    'MAINNET': {'NAME': 'MAINNET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 60, 'BLOCKS_PER_CYCLE': 4096,
                'BLOCKS_PER_ROLL_SNAPSHOT': 256, 'BLOCK_REWARD': 40000000, 'ENDORSEMENT_REWARD': 1250000},
    CURRENT_TESTNET: {'NAME': CURRENT_TESTNET, 'NB_FREEZE_CYCLE': 3, 'BLOCK_TIME_IN_SEC': 30, 'BLOCKS_PER_CYCLE': 2048,
                      'BLOCKS_PER_ROLL_SNAPSHOT': 128, 'BLOCK_REWARD': 40000000, 'ENDORSEMENT_REWARD': 1250000},
}


TEZOS_RPC_PORT = 8732

MUTEZ = 1e6

VERSION = 8.0


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
    TRD does not know its fate.
    """
    UNDEFINED = -1
    FAIL = 0
    PAID = 1
    DONE = 2
    INJECTED = 3

    def is_fail(self):
        return self.value == 0

    def is_processed(self):
        return self.value > 0

    def __str__(self):
        return self.name


class RewardsType(Enum):
    ACTUAL = 'actual'
    IDEAL = 'ideal'

    def isIdeal(self):
        return self == RewardsType.IDEAL

    def isActual(self):
        return self == RewardsType.ACTUAL

    def __str__(self):
        return self.value
