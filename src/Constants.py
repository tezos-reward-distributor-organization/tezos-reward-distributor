from enum import Enum

EXIT_PAYMENT_TYPE = "exit"
PROTOCOL_NAME = 'hangzhou'
CURRENT_TESTNET = ('{}2net'.format(PROTOCOL_NAME)).upper()


FIRST_GRANADA_LEVEL = 1589249

# Providers api prefix
# Public RPC
PUBLIC_NODE_URL = {
    'MAINNET': 'https://mainnet-tezos.giganode.io',
    CURRENT_TESTNET: 'https://testnet-tezos.giganode.io'
}

# TzStats
TZSTATS_PUBLIC_API_URL = {
    'MAINNET': 'https://api.tzstats.com',
    CURRENT_TESTNET: 'https://api.{}.tzstats.com'.format(PROTOCOL_NAME)
}

# TzKT
TZKT_PUBLIC_API_URL = {
    'MAINNET': 'https://api.tzkt.io/v1',
    CURRENT_TESTNET: 'https://api.{}.tzkt.io/v1'.format(CURRENT_TESTNET).lower()
}


# Network constants
DEFAULT_NETWORK_CONFIG_MAP = {
    'MAINNET': {'NAME': 'MAINNET', 'NB_FREEZE_CYCLE': 5, 'BLOCK_TIME_IN_SEC': 60, 'MINIMAL_BLOCK_DELAY': 30, 'BLOCKS_PER_CYCLE': 8192,
                'BLOCKS_PER_ROLL_SNAPSHOT': 512, 'BLOCK_REWARD': 20000000, 'ENDORSEMENT_REWARD': 78125},
    CURRENT_TESTNET: {'NAME': CURRENT_TESTNET, 'NB_FREEZE_CYCLE': 3, 'BLOCK_TIME_IN_SEC': 15, 'MINIMAL_BLOCK_DELAY': 15, 'BLOCKS_PER_CYCLE': 4096,
                      'BLOCKS_PER_ROLL_SNAPSHOT': 256, 'BLOCK_REWARD': 20000000, 'ENDORSEMENT_REWARD': 78125},
}


TEZOS_RPC_PORT = 8732

MUTEZ = 1e6

VERSION = 10.0

DISK_LIMIT_PERCENTAGE = 0.1

GIGA_BYTE = 1e9


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
    ACTUAL = 'actual'
    IDEAL = 'ideal'
    ESTIMATED = 'estimated'

    def isEstimated(self):
        return self == RewardsType.ESTIMATED

    def isActual(self):
        return self == RewardsType.ACTUAL

    def isIdeal(self):
        return self == RewardsType.IDEAL

    def __str__(self):
        return self.value
