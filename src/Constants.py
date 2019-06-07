from enum import Enum

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
    UNKNOWN = 3

    def is_fail(self):
        return self.value == 0

    def is_processed(self):
        return self.value > 0

    def __str__(self):
        return self.name