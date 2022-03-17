import csv
from log_config import main_logger
from Constants import RewardsType

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
        rl.staking_balance = int(row["staked_balance"])
        rl.current_balance = int(row["current_balance"])
        rl.ratio = float(row["ratio"])
        rl.service_fee_ratio = float(row["fee_ratio"])
        rl.amount = int(row["amount"])
        rl.service_fee_amount = int(row["fee_amount"])
        rl.service_fee_rate = float(row["fee_rate"])
        if "overestimate" in row:
            rl.overestimate = (
                int(0) if row["overestimate"] == "pending" else int(row["overestimate"])
            )
        else:
            rl.overestimate = 0
        rl.adjustment = int(row["adjustment"]) if "adjustment" in row else int(0)
        rl.adjusted_amount = int(
            row["adjusted_amount"] if "adjusted_amount" in row else int(row["amount"])
        )
        rl.payable = int(row["payable"])
        rl.skippedatphase = int(row["skipped"])
        rl.desc = str(row["desc"])
        rl.paymentaddress = str(row["address"])
        if row["rewards_type"] == "E":
            rl.rewards_type = RewardsType.ESTIMATED
        elif row["rewards_type"] == "A":
            rl.rewards_type = RewardsType.ACTUAL
        elif row["rewards_type"] == "I":
            rl.rewards_type = RewardsType.IDEAL

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
        # TODO: Think about chaning this to the actual strings
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

            # Note: values for True and False are marked with "0" and "1" in the excel for backwards compatibility

            # First row is for the baker
            csv_writer.writerow(
                [
                    str(baking_address),  # address
                    str("B"),  # type
                    int(
                        sum([pl.staking_balance for pl in payment_logs])
                    ),  # staking_balance
                    int(1),  # current_balance
                    "{0:10f}".format(1.0),  # ratio
                    "{0:10f}".format(0.0),  # service_fee_ratio
                    int(total_rewards),  # amount
                    int(0),  # service_fee_amount
                    "{0:f}".format(0.0),  # service_fee_rate
                    (
                        "pending"
                        if early_payout
                        else int(sum([pl.overestimate for pl in payment_logs]))
                    ),  # overestimate
                    int(sum([pl.adjustment for pl in payment_logs])),  # adjustments
                    int(
                        sum([pl.adjusted_amount for pl in payment_logs])
                    ),  # adjustment_amounts
                    int(0),  # not payable
                    int(0),  # not skipped
                    int(-1),  #
                    str("Baker"),
                    str("None"),
                    str(rt),
                ]
            )

            for pymnt_log in payment_logs:
                # write row to csv file
                array = [
                    str(pymnt_log.address),
                    str(pymnt_log.type),
                    int(pymnt_log.staking_balance),
                    int(pymnt_log.current_balance),
                    "{0:.10f}".format(pymnt_log.ratio),
                    "{0:.10f}".format(pymnt_log.service_fee_ratio),
                    int(pymnt_log.amount),
                    int(pymnt_log.service_fee_amount),
                    "{0:f}".format(pymnt_log.service_fee_rate),
                    ("pending" if early_payout else int(pymnt_log.overestimate)),
                    int(pymnt_log.adjustment),
                    int(pymnt_log.adjusted_amount),
                    int(1) if pymnt_log.payable else int(0),
                    int(1) if pymnt_log.skipped else int(0),
                    pymnt_log.skippedatphase if pymnt_log.skipped else int(-1),
                    pymnt_log.desc if pymnt_log.desc else str("None"),
                    str(pymnt_log.paymentaddress),
                    str(rt),
                ]
                csv_writer.writerow(array)

                logger.debug(
                    "Reward created for {:s} type: {:s}, stake bal: {:<,d} mutez, cur bal: {:<,d} mutez, ratio: {:.6f}, fee_ratio: {:.6f}, "
                    "amount: {:<,d} mutez, fee_amount: {:<,d} mutez, fee_rate: {:.2f}, overestimate: {}, adjustment: {:<,d}, adjustment_amount: {:<,d}, payable: {:d}, skipped: {:d}, at-phase: {:d}, "
                    "desc: {:s}, pay_addr: {:s}, type: {:s}".format(
                        pymnt_log.address,
                        pymnt_log.type,
                        pymnt_log.staking_balance,
                        pymnt_log.current_balance,
                        pymnt_log.ratio,
                        pymnt_log.service_fee_ratio,
                        pymnt_log.amount,
                        pymnt_log.service_fee_amount,
                        pymnt_log.service_fee_rate,
                        "pending"
                        if early_payout
                        else "{:d}".format(int(pymnt_log.overestimate)),
                        pymnt_log.adjustment,
                        pymnt_log.adjusted_amount,
                        int(1) if pymnt_log.payable else int(0),
                        int(1) if pymnt_log.skipped else int(0),
                        pymnt_log.skippedatphase,
                        pymnt_log.desc,
                        pymnt_log.paymentaddress,
                        rt,
                    )
                )

        logger.info("Calculation report is created at '{}'".format(report_file))
