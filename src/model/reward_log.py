TYPE_DELEGATOR = "D"
TYPE_FOUNDER = "F"
TYPE_OWNER = "O"
TYPE_OWNERS_PARENT = "OWNERS_PARENT"
TYPE_FOUNDERS_PARENT = "FOUNDERS_PARENT"
TYPE_MERGED = "MERGED"


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
