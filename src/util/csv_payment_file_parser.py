import csv

from Constants import PaymentStatus
from model.reward_log import RewardLog


class CsvPaymentFileParser:
    def __init__(self) -> None:
        super().__init__()

    def parse(self, payment_report_file, cycle):
        with open(payment_report_file) as f:
            # read csv into list of dictionaries
            dict_rows = [
                {key: value for key, value in row.items()}
                for row in csv.DictReader(f, delimiter=",", skipinitialspace=True)
            ]

            records = [self.from_payment_csv_dict_row(row, cycle) for row in dict_rows]

            return records

    @staticmethod
    def from_payment_csv_dict_row(row, cycle):
        reward_log = RewardLog(row["address"], row["type"], 0, 0)
        reward_log.cycle = cycle
        reward_log.amount = int(row["amount"])
        reward_log.hash = None if row["hash"] == "None" else row["hash"]
        reward_log.paid = PaymentStatus(int(row["paid"]))

        return reward_log

    @staticmethod
    def write(report_file, payment_logs):
        try:
            with open(report_file, "w") as f:
                csv_writer = csv.writer(
                    f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
                )
                csv_writer.writerow(
                    [
                        "address",
                        "type",
                        "amount",
                        "hash",
                        "paid",
                        "delegate_transaction_fee",
                        "delegator_transaction_fee",
                    ]
                )

                for payment_log in payment_logs:
                    csv_writer.writerow(
                        [
                            payment_log.paymentaddress,
                            payment_log.type,
                            payment_log.amount,
                            payment_log.hash if payment_log.hash else "None",
                            payment_log.paid.value,
                            payment_log.delegate_transaction_fee,
                            payment_log.delegator_transaction_fee,
                        ]
                    )

        except Exception as e:
            import errno

            print("Exception during write operation invoked: {}".format(e))
            if e.errno == errno.ENOSPC:
                print("Not enough space on device!")
            exit()
