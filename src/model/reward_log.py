from enum import Enum

from Constants import EXIT_PAYMENT_TYPE

TYPE_DELEGATOR = "D"
TYPE_FOUNDER = "F"
TYPE_OWNER = "O"
TYPE_OWNERS_PARENT = "OWNERS_PARENT"
TYPE_FOUNDERS_PARENT = "FOUNDERS_PARENT"
TYPE_MERGED = "M"

TYPE_EXTERNAL = "E"


# TYPE_MERGED = "MERGED"


class RunMode(Enum):
    FOREVER = 1
    PENDING = 2
    ONETIME = 3


class RewardLog:
    def __init__(self, address, type, balance) -> None:
        super().__init__()
        self.balance = balance
        self.address = address
        self.paymentaddress = address
        self.type = type
        self.desc = ""
        self.skipped = False
        self.skippedatphase = 0
        self.ratio0 = 0
        self.ratio1 = 0
        self.ratio2 = 0
        self.ratio3 = 0
        self.ratio4 = 0
        self.ratio5 = 0
        self.ratio = 0

        self.service_fee_amount = 0
        self.service_fee_rate = 0
        self.service_fee_ratio = 0
        self.amount = 0
        self.parents = None

        self.paid = False
        self.hash = "0"
        self.payable = True

    def skip(self, desc, phase):
        if self.skipped:
            return

        self.skipped = True
        self.desc += desc
        self.skippedatphase = phase
        self.payable = False

        return self

    def __repr__(self) -> str:
        return "address: %s, type: %s, balance: %s, disabled:%s" % (self.address, self.type, self.balance, self.skipped)

    @staticmethod
    def ExitInstance():
        return RewardLog(address=EXIT_PAYMENT_TYPE, type=EXIT_PAYMENT_TYPE, balance=0)

    @staticmethod
    def ExternalInstance(file_name, address, amount):
        rl = RewardLog(address, TYPE_EXTERNAL, 0)
        rl.amount = amount
        rl.desc = file_name
        return rl


def cmp_by_skip_type_balance(rl1, rl2):
    types = {TYPE_DELEGATOR: 5, TYPE_OWNER: 4, TYPE_FOUNDER: 3, TYPE_OWNERS_PARENT: 2, TYPE_FOUNDERS_PARENT: 1,
             TYPE_MERGED: 0}
    if rl1.skipped == rl2.skipped:
        if rl1.type == rl2.type:
            if rl1.balance is None:
                return 1
            if rl2.balance is None:
                return -1
            if rl1.balance == rl2.balance:
                return 1
            else:
                return rl2.balance - rl1.balance
        else:
            return types[rl2.type] - types[rl1.type]
    else:
        if not rl2.skipped:
            return 1
        else:
            return -1


def cmp_by_type_balance(rl1, rl2):
    types = {TYPE_DELEGATOR: 5, TYPE_OWNER: 4, TYPE_FOUNDER: 3, TYPE_OWNERS_PARENT: 2, TYPE_FOUNDERS_PARENT: 1,
             TYPE_MERGED: 0}

    if rl1.type == rl2.type:
        if rl1.balance is None:
            return 1
        if rl2.balance is None:
            return -1
        if rl1.balance == rl2.balance:
            return 1
        else:
            return rl2.balance - rl1.balance
    else:
        return types[rl2.type] - types[rl1.type]
