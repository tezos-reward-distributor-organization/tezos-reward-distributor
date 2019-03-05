from enum import Enum

TYPE_DELEGATOR = "D"
TYPE_FOUNDER = "F"
TYPE_OWNER = "O"
TYPE_OWNERS_PARENT = "OWNERS_PARENT"
TYPE_FOUNDERS_PARENT = "FOUNDERS_PARENT"
TYPE_MERGED = "MERGED"


class RunMode(Enum):
    FOREVER = 1
    PENDING = 2
    ONETIME = 3


class RewardLog:
    def __init__(self, address, type, balance) -> None:
        super().__init__()
        self.balance = balance
        self.address = address
        self.type = type
        self.desc = ""
        self.skipped = False
        self.skippedatphase = None
        self.ratio0 = None
        self.ratio1 = None
        self.ratio2 = None
        self.ratio3 = None
        self.ratio4 = None
        self.ratio5 = None

    @staticmethod
    def RewardLog5(addr, type, ratio5):
        rl5 = RewardLog(addr, type, None)
        rl5.ratio5 = ratio5

        return rl5

    def skip(self, desc, phase):
        if self.skipped:
            return

        self.skipped = True
        self.desc += desc
        self.skippedatphase = phase

        return self


def cmp(rl1, rl2):
    types={TYPE_DELEGATOR:5,TYPE_OWNER:4,TYPE_FOUNDER:3,TYPE_OWNERS_PARENT:2,TYPE_FOUNDERS_PARENT:1,TYPE_MERGED:0}
    if rl1.skipped == rl2.skipped:
        if rl1.type == rl2.type:
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
