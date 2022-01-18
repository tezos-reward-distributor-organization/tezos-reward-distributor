import csv
from log_config import main_logger
from Constants import MUTEZ, RewardsType

from model.reward_log import RewardLog

logger = main_logger.getChild("payment_producer")


class CsvCalculationFileParser:
    def __init__(self) -> None:
        super().__init__()

    def parse(self, calculation_file, baking_address):
        with open(calculation_file) as f:
            # read csv into list of dictionaries
            dict_rows = [
                {key: value for key, value in row.items()}
                for row in csv.DictReader(f, delimiter=",", skipinitialspace=True)
            ]

            records = [
                self.from_payment_csv_dict_row(row)
                for row in dict_rows
                if row["address"] != baking_address
            ]
            baker_record = [
                self.from_payment_csv_dict_row(row)
                for row in dict_rows
                if row["address"] == baking_address
            ][0]

            return records, baker_record.amount, RewardsType(baker_record.rewards_type)

    @staticmethod
    def from_payment_csv_dict_row(row):
        rl = RewardLog(row["address"], row["type"], 0, 0)
        rl.ratio = float(row["ratio"])
        rl.staking_balance = int(row["staked_balance"])
        rl.current_balance = int(float(row["current_balance"]))
        rl.service_fee_ratio = float(row["fee_ratio"])
        rl.amount = float(row["amount"])
        rl.service_fee_amount = float(row["fee_amount"])
        rl.service_fee_rate = float(row["fee_rate"])
        if "overestimate" in row:
            rl.overestimate = None if row["overestimate"] == "pending" else float(row["overestimate"])
        else:
            rl.overestimate = 0
        rl.adjustment = float(row["adjustment"]) if "adjustment" in row else float(0)
        rl.adjusted_amount = float(
            row["adjusted_amount"] if "adjusted_amount" in row else row["amount"]
        )
        rl.payable = int(row["payable"])
        rl.skippedatphase = int(row["skipped"])
        rl.desc = row["desc"]
        rl.paymentaddress = row["address"]
        if row["rewards_type"] == "E":
            rl.rewards_type = "estimated"
        elif row["rewards_type"] == "A":
            rl.rewards_type = "actual"
        elif row["rewards_type"] == "I":
            rl.rewards_type = "ideal"

        return rl

    @staticmethod
    def write(
        payment_logs,
        report_file,
        total_rewards,
        rewards_type,
        baking_address,
        early_payout,
    ):
        if rewards_type.isEstimated():
            rt = "E"
        elif rewards_type.isActual():
            rt = "A"
        elif rewards_type.isIdeal():
            rt = "I"

        with open(report_file, "w") as f:
            csv_writer = csv.writer(
                f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            # write headers and total rewards
            csv_writer.writerow(
                [
                    "address",
                    "type",
                    "staked_balance",
                    "current_balance",
                    "ratio",
                    "fee_ratio",
                    "amount",
                    "fee_amount",
                    "fee_rate",
                    "overestimate",
                    "adjustment",
                    "adjusted_amount",
                    "payable",
                    "skipped",
                    "atphase",
                    "desc",
                    "payment_address",
                    "rewards_type",
                ]
            )

            # First row is for the baker
            csv_writer.writerow(
                [
                    baking_address,
                    "B",
                    sum([pl.staking_balance for pl in payment_logs]),
                    "{0:f}".format(1.0),
                    "{0:f}".format(1.0),
                    "{0:f}".format(0.0),
                    "{0:f}".format(total_rewards),
                    "{0:f}".format(0.0),
                    "{0:f}".format(0.0),
                    (
                        "pending"
                        if early_payout
                        else "{0:f}".format(
                            sum([pl.overestimate for pl in payment_logs])
                        )
                    ),
                    "{0:f}".format(sum([pl.adjustment for pl in payment_logs])),
                    "{0:f}".format(sum([pl.adjusted_amount for pl in payment_logs])),
                    "0",
                    "0",
                    "-1",
                    "Baker",
                    "None",
                    rt,
                ]
            )

            for pymnt_log in payment_logs:
                # write row to csv file
                array = [
                    pymnt_log.address,
                    pymnt_log.type,
                    pymnt_log.staking_balance,
                    pymnt_log.current_balance,
                    "{0:.10f}".format(pymnt_log.ratio),
                    "{0:.10f}".format(pymnt_log.service_fee_ratio),
                    "{0:f}".format(pymnt_log.amount),
                    "{0:f}".format(pymnt_log.service_fee_amount),
                    "{0:f}".format(pymnt_log.service_fee_rate),
                    (
                        "pending"
                        if early_payout
                        else "{0:f}".format(float(pymnt_log.overestimate))
                    ),
                    "{0:f}".format(pymnt_log.adjustment),
                    "{0:f}".format(pymnt_log.adjusted_amount),
                    "1" if pymnt_log.payable else "0",
                    "1" if pymnt_log.skipped else "0",
                    pymnt_log.skippedatphase if pymnt_log.skipped else "-1",
                    pymnt_log.desc if pymnt_log.desc else "None",
                    pymnt_log.paymentaddress,
                    rt,
                ]
                csv_writer.writerow(array)

                logger.debug(
                    "Reward created for {:s} type: {:s}, stake bal: {:>10.2f}, cur bal: {:>10.2f}, ratio: {:.6f}, fee_ratio: {:.6f}, "
                    "amount: {:>10.6f}, fee_amount: {:>4.6f}, fee_rate: {:.2f}, payable: {:s}, skipped: {:s}, at-phase: {:d}, "
                    "desc: {:s}, pay_addr: {:s}, type: {:s}".format(
                        pymnt_log.address,
                        pymnt_log.type,
                        pymnt_log.staking_balance / MUTEZ,
                        pymnt_log.current_balance / MUTEZ,
                        pymnt_log.ratio,
                        pymnt_log.service_fee_ratio,
                        pymnt_log.amount / MUTEZ,
                        pymnt_log.service_fee_amount / MUTEZ,
                        pymnt_log.service_fee_rate,
                        "Y" if pymnt_log.payable else "N",
                        "Y" if pymnt_log.skipped else "N",
                        pymnt_log.skippedatphase,
                        pymnt_log.desc,
                        pymnt_log.paymentaddress,
                        rt,
                    )
                )

        logger.info("Calculation report is created at '{}'".format(report_file))
