from enum import Enum

EXIT_PAYMENT_TYPE = "exit"

PUBLIC_NODE_URL = {"MAINNET": ["https://mainnet-tezos.giganode.io", "https://teznode.letzbake.com"],
                   "DELPHINET": ["https://tezos-dev.cryptonomic-infra.tech", "https://delphinet-tezos.giganode.io"]
                   }

TEZOS_RPC_PORT = 8732

VERSION = 8.0


class RunMode(Enum):
    FOREVER = 1
    PENDING = 2
    ONETIME = 3
    RETRY_FAILED = 4


class PaymentStatus(Enum):
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
