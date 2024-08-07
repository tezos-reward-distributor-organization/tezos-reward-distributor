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
        self, address, type, delegating_balance, current_balance, originaladdress=None
    ) -> None:
        super().__init__()
        self.delegating_balance = int(delegating_balance)
        self.current_balance = int(current_balance)
        self.address = str(address)
        self.paymentaddress = str(address)
        self.originaladdress = (
            str(originaladdress) if originaladdress is not None else str(address)
        )
        self.needs_activation = False
        self.type = str(type)
        self.desc = str("")
        self.skipped = False
        self.overestimate = int(0)
        self.skippedatphase = int(0)
        self.cycle = int(0)
        self.ratio0 = float(0.0)
        self.ratio1 = float(0.0)
        self.ratio2 = float(0.0)
        self.ratio3 = float(0.0)
        self.ratio4 = float(0.0)
        self.ratio5 = float(0.0)
        self.ratio = float(0.0)
        self.service_fee_amount = int(0)
        self.service_fee_rate = float(0.0)
        self.service_fee_ratio = float(0.0)
        self.amount = int(0)
        self.adjusted_amount = int(0)
        self.adjustment = int(0)
        self.delegate_transaction_fee = int(0)
        self.delegator_transaction_fee = int(0)
        self.parents = None
        self.paid = PaymentStatus.UNDEFINED
        self.hash = None
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
            self.delegating_balance,
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
            delegating_balance=0,
            current_balance=0,
        )

    @staticmethod
    def ExternalInstance(file_name, address, amount):
        rl = RewardLog(address, TYPE_EXTERNAL, 0, 0)
        rl.adjusted_amount = amount
        rl.desc += file_name
        return rl


def cmp_by_skip_type_balance(rl1, rl2):
    if rl1.skipped == rl2.skipped:
        if rl1.type == rl2.type:
            if rl1.delegating_balance is None:
                return 1
            if rl2.delegating_balance is None:
                return -1
            if rl1.delegating_balance == rl2.delegating_balance:
                return 1
            else:
                return rl2.delegating_balance - rl1.delegating_balance
        else:
            return types[rl2.type] - types[rl1.type]
    else:
        if not rl2.skipped:
            return 1
        else:
            return -1


def cmp_by_type_balance(rl1, rl2):
    if rl1.type == rl2.type:
        if rl1.delegating_balance is None:
            return 1
        if rl2.delegating_balance is None:
            return -1
        if rl1.delegating_balance == rl2.delegating_balance:
            return 1
        else:
            return rl2.delegating_balance - rl1.delegating_balance
    else:
        return types[rl2.type] - types[rl1.type]
