from enum import Enum

EXIT_PAYMENT_TYPE = "exit"


class RunMode(Enum):
    FOREVER = 1
    PENDING = 2
    ONETIME = 3

