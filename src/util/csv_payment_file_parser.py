import csv

from Constants import PaymentStatus
from model.reward_log import RewardLog


class CsvPaymentFileParser:
    def __init__(self) -> None:
        super().__init__()

    def parse(self, payment_failed_report_file, cycle):
        with open(payment_failed_report_file) as f:
            # read csv into list of dictionaries
            dict_rows = [{key: value for key, value in row.items()} for row in
                         csv.DictReader(f, delimiter=',', skipinitialspace=True)]

            records = [self.FromPaymentCSVDictRow(row, cycle) for row in dict_rows]

            return records

    def FromPaymentCSVDictRow(self, row, cycle):
        rl = RewardLog(row["address"], row["type"], 0, 0)
        rl.cycle = cycle
        rl.amount = int(row["amount"])
        rl.hash = None if row["hash"] == 'None' else row["hash"]
        rl.paid = PaymentStatus(int(row["paid"]))

        return rl

    def write(self, report_file, payment_logs):
        with open(report_file, "w") as f:
            csv_writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["address", "type", "amount", "hash", "paid"])

            for pl in payment_logs:
                # write row to csv file
                csv_writer.writerow([pl.paymentaddress, pl.type, pl.amount, pl.hash if pl.hash else "None", pl.paid.value])
