from enum import Enum

MUTEZ = 1e+6

EXIT_PAYMENT_TYPE = "exit"


class RunMode(Enum):
    FOREVER = 1
    PENDING = 2
    ONETIME = 3


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

PUBLIC_NODE_URL = { "MAINNET": ["https://mainnet-tezos.giganode.io", "https://teznode.letzbake.com"],
                    "ALPHANET": ["https://tezos-dev.cryptonomic-infra.tech", "https://testnet-tezos.giganode.io"],
                    "ZERONET": ["https://rpczero.tzbeta.net"]}
