from Constants import EXIT_PAYMENT_TYPE, PaymentStatus

TYPE_DELEGATOR = "D"
TYPE_FOUNDER = "F"
TYPE_OWNER = "O"
TYPE_OWNERS_PARENT = "OWNERS_PARENT"
TYPE_FOUNDERS_PARENT = "FOUNDERS_PARENT"
TYPE_MERGED = "M"
TYPE_EXTERNAL = "E"

types = {
    TYPE_DELEGATOR: 5,
    TYPE_OWNER: 4,
    TYPE_FOUNDER: 3,
    TYPE_OWNERS_PARENT: 2,
    TYPE_FOUNDERS_PARENT: 1,
    TYPE_MERGED: 0,
}


class RewardLog:
    def __init__(
        self, address, type, staking_balance, current_balance, originaladdress=None
    ) -> None:
        super().__init__()
        self.staking_balance = staking_balance
        self.current_balance = current_balance
        self.address = address
        self.paymentaddress = address
        self.originaladdress = (
            originaladdress if originaladdress is not None else address
        )
        self.needs_activation = False
        self.type = type
        self.desc = ""
        self.skipped = False
        self.overestimate = 0
        self.skippedatphase = 0
        self.cycle = 0
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
        self.adjusted_amount = 0
        self.adjustment = 0
        self.parents = None

        self.paid = PaymentStatus.UNDEFINED
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
        return "Address: {} ({}), T: {}, SB: {}, CB: {}, Amt: {}, AdjAmt: {}, Skp: {}, NA: {}".format(
            self.address,
            self.paymentaddress,
            self.type,
            self.staking_balance,
            self.current_balance,
            self.amount,
            self.adjusted_amount,
            self.skipped,
            self.needs_activation,
        )

    @staticmethod
    def ExitInstance():
        return RewardLog(
            address=EXIT_PAYMENT_TYPE,
            type=EXIT_PAYMENT_TYPE,
            staking_balance=0,
            current_balance=0,
        )

    @staticmethod
    def ExternalInstance(file_name, address, amount):
        rl = RewardLog(address, TYPE_EXTERNAL, 0)
        rl.amount = amount
        rl.desc = file_name
        return rl


def cmp_by_skip_type_balance(rl1, rl2):

    if rl1.skipped == rl2.skipped:
        if rl1.type == rl2.type:
            if rl1.staking_balance is None:
                return 1
            if rl2.staking_balance is None:
                return -1
            if rl1.staking_balance == rl2.staking_balance:
                return 1
            else:
                return rl2.staking_balance - rl1.staking_balance
        else:
            return types[rl2.type] - types[rl1.type]
    else:
        if not rl2.skipped:
            return 1
        else:
            return -1


def cmp_by_type_balance(rl1, rl2):

    if rl1.type == rl2.type:
        if rl1.staking_balance is None:
            return 1
        if rl2.staking_balance is None:
            return -1
        if rl1.staking_balance == rl2.staking_balance:
            return 1
        else:
            return rl2.staking_balance - rl1.staking_balance
    else:
        return types[rl2.type] - types[rl1.type]
