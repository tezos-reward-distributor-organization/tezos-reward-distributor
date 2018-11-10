from Constants import EXIT_PAYMENT_TYPE


class PaymentRecord():
    def __init__(self, cycle=None, address=None, ratio=None, fee_rate=None, reward=None, fee=None, type=None,
                 payment=None, paid=False, hash=""):
        self.cycle = cycle
        self.address = address
        self.ratio = ratio
        self.fee_rate = fee_rate
        self.reward = reward
        self.fee = fee
        self.type = type
        self.payment = payment
        self.paid = paid
        self.hash = hash

    @staticmethod
    def BakerInstance(cycle, address, reward):
        return PaymentRecord(cycle, address, 1, 0, reward, 0, 'B', reward)

    @staticmethod
    def FounderInstance(cycle, address, ratio, payment):
        return PaymentRecord(cycle, address, ratio, 0, 0, 0, 'F', payment)

    @staticmethod
    def OwnerInstance(cycle, address, ratio, reward, payment):
        return PaymentRecord(cycle, address, ratio, 0, reward, 0, 'O', payment)

    @staticmethod
    def DelegatorInstance(cycle, address, ratio, fee_rate, reward, fee, payment):
        return PaymentRecord(cycle, address, ratio, fee_rate, reward, fee, 'D', payment)

    @staticmethod
    def ExitInstance():
        return PaymentRecord(type=EXIT_PAYMENT_TYPE)

    @staticmethod
    def FromPaymentCSVDictRow(row):
        return PaymentRecord(row["cycle"], row["address"], row["ratio"], row["fee_rate"], row["reward"], row["fee"],
                             row["type"], row["payment"], row["paid"], row["hash"])

    @staticmethod
    def FromPaymentCSVDictRows(rows):
        items = []
        for row in rows:
            items.append(PaymentRecord.FromPaymentCSVDictRow(row))

        return items
