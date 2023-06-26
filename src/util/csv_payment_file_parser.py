import csv

from Constants import PaymentStatus
from model.reward_log import RewardLog
from util.exit_program import exit_program, ExitCode


class CsvPaymentFileParser:
    def __init__(self) -> None:
        super().__init__()

    def parse(self, payment_report_file, cycle):
        with open(payment_report_file, newline="") as f:
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
        reward_log.adjusted_amount = int(row["amount"])
        reward_log.hash = None if row["hash"] == "None" else row["hash"]
        reward_log.paid = PaymentStatus[str(row["paid"]).upper()]
        reward_log.desc = str(row["description"])

        return reward_log

    @staticmethod
    def write(report_file, payment_logs):
        try:
            with open(report_file, "w", newline="") as f:
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
                        "description",
                    ]
                )

                for payment_log in payment_logs:
                    csv_writer.writerow(
                        [
                            str(payment_log.paymentaddress),
                            str(payment_log.type),
                            int(payment_log.adjusted_amount),
                            str(payment_log.hash) if payment_log.hash else "None",
                            str(payment_log.paid.name).lower(),
                            str(payment_log.desc),
                        ]
                    )

        except Exception as e:
            import errno

            if e.errno == errno.ENOSPC:
                error_msg = "Exception during write operation invoked: {}. Not enough space on device.".format(
                    e
                )
                exit_program(ExitCode.NO_SPACE, error_msg)
            else:
                error_msg = "Exception during write operation invoked: {}".format(e)
                exit_program(ExitCode.GENERAL_ERROR, error_msg)
