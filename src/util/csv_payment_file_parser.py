import csv

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

    def FromPaymentCSVDictRow(self, row, cyle):
        try:
            paid = int(row["paid"])
            paid = paid > 0
        except ValueError as ve:
            raise Exception("Unable to read paid value.") from ve

        rl = RewardLog(row["address"], row["type"], None)
        rl.cycle = cyle
        rl.amount = int(row["amount"])
        rl.hash = None if row["hash"] == 'None' else row["hash"]
        rl.balance = 0 if rl.balance == None else rl.balance
        rl.paid = paid
        # rl.child = None if row["child"] == 'None' else row["child"]

        return rl