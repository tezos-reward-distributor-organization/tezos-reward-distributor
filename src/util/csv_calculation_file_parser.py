import csv
from log_config import main_logger
from Constants import RewardsType

from model.reward_log import RewardLog

logger = main_logger.getChild("payment_producer")


class CsvCalculationFileParser:
    def __init__(self) -> None:
        super().__init__()

    def parse(self, calculation_file, baking_address):
        with open(calculation_file, newline="") as f:
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

            return (
                records,
                baker_record.amount,
                RewardsType.ACTUAL,
                False,
            )

    @staticmethod
    def from_payment_csv_dict_row(row):
        rl = RewardLog(row["address"], row["type"], 0, 0)
        rl.delegating_balance = int(row["delegated_balance"])
        rl.current_balance = int(row["current_balance"])
        rl.ratio = float(row["ratio"])
        rl.service_fee_ratio = float(row["fee_ratio"])
        rl.amount = int(row["amount"])
        rl.service_fee_amount = int(row["fee_amount"])
        rl.service_fee_rate = float(row["fee_rate"])
        rl.overestimate = int(0)
        rl.adjustment = int(0)
        rl.adjusted_amount = int(row["amount"])
        if "delegate_transaction_fee" in row:
            rl.delegate_transaction_fee = (
                int(0)
                if row["delegate_transaction_fee"] == "pending"
                else int(row["delegate_transaction_fee"])
            )
        else:
            rl.delegate_transaction_fee = int(0)
        if "delegator_transaction_fee" in row:
            rl.delegator_transaction_fee = (
                int(0)
                if row["delegator_transaction_fee"] == "pending"
                else int(row["delegator_transaction_fee"])
            )
        else:
            rl.delegator_transaction_fee = int(0)
        rl.payable = True if int(row["payable"]) == 1 else False
        rl.skipped = True if int(row["skipped"]) == 1 else False
        rl.skippedatphase = int(row["atphase"])
        rl.desc = str(row["desc"])
        rl.paymentaddress = str(row["payment_address"])

        return rl

    @staticmethod
    def write(
        payment_logs,
        report_file,
        total_rewards,
        rewards_type,
        baking_address,
        early_payout,
        fees_simulated=False,
    ):
        rt = "A"

        with open(report_file, "w", newline="") as f:
            csv_writer = csv.writer(
                f, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL
            )
            # write headers and total rewards
            csv_writer.writerow(
                [
                    "address",
                    "type",
                    "delegated_balance",
                    "current_balance",
                    "ratio",
                    "fee_ratio",
                    "amount",
                    "fee_amount",
                    "fee_rate",
                    "overestimate",
                    "adjustment",
                    "adjusted_amount",
                    "delegate_transaction_fee",
                    "delegator_transaction_fee",
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
                        sum([pl.delegating_balance for pl in payment_logs])
                    ),  # delegating_balance
                    int(1),  # current_balance
                    "{0:10f}".format(1.0),  # ratio
                    "{0:10f}".format(0.0),  # service_fee_ratio
                    int(total_rewards),  # amount
                    int(0),  # service_fee_amount
                    "{0:f}".format(0.0),  # service_fee_rate
                    0,
                    int(sum([pl.adjustment for pl in payment_logs])),  # adjustments
                    int(
                        sum([pl.adjusted_amount for pl in payment_logs])
                    ),  # adjustment_amounts
                    (
                        "pending"
                        if not fees_simulated
                        else int(
                            sum([pl.delegate_transaction_fee for pl in payment_logs])
                        )
                    ),  # delegate_transaction_fees
                    (
                        "pending"
                        if not fees_simulated
                        else int(
                            sum([pl.delegator_transaction_fee for pl in payment_logs])
                        )
                    ),  # delegator_transaction_fees
                    int(0),  # not payable
                    int(0),  # not skipped
                    int(-1),  # atphase
                    str("Baker"),  # desc
                    str("None"),  # payment_address
                    str(rt),  # rewards_type
                ]
            )

            for pymnt_log in payment_logs:
                # write row to csv file
                array = [
                    str(pymnt_log.address),
                    str(pymnt_log.type),
                    int(pymnt_log.delegating_balance),
                    int(pymnt_log.current_balance),
                    "{0:.10f}".format(pymnt_log.ratio),
                    "{0:.10f}".format(pymnt_log.service_fee_ratio),
                    int(pymnt_log.amount),
                    int(pymnt_log.service_fee_amount),
                    "{0:f}".format(pymnt_log.service_fee_rate),
                    0,
                    int(pymnt_log.adjustment),
                    int(pymnt_log.adjusted_amount),
                    (
                        "pending"
                        if not fees_simulated
                        else int(pymnt_log.delegate_transaction_fee)
                    ),
                    (
                        "pending"
                        if not fees_simulated
                        else int(pymnt_log.delegator_transaction_fee)
                    ),
                    int(1) if pymnt_log.payable else int(0),
                    int(1) if pymnt_log.skipped else int(0),
                    pymnt_log.skippedatphase if pymnt_log.skipped else int(-1),
                    str(pymnt_log.desc),
                    str(pymnt_log.paymentaddress),
                    str(rt),
                ]
                csv_writer.writerow(array)

                logger.debug(
                    "Reward created for {:s} type: {:s}, stake bal: {:<,d} mutez, cur bal: {:<,d} mutez, ratio: {:.6f}, fee_ratio: {:.6f}, "
                    "amount: {:<,d} mutez, fee_amount: {:<,d} mutez, fee_rate: {:.2f}, overestimate: {}, adjustment: {:<,d}, adjustment_amount: {:<,d}, delegate_transaction_fee: {}, delegator_transaction_fee: {}, payable: {:d}, skipped: {:d}, at-phase: {:d}, "
                    "desc: {:s}, pay_addr: {:s}, type: {:s}".format(
                        pymnt_log.address,
                        pymnt_log.type,
                        pymnt_log.delegating_balance,
                        pymnt_log.current_balance,
                        pymnt_log.ratio,
                        pymnt_log.service_fee_ratio,
                        pymnt_log.amount,
                        pymnt_log.service_fee_amount,
                        pymnt_log.service_fee_rate,
                        "{:d}".format(int(pymnt_log.overestimate)),
                        pymnt_log.adjustment,
                        pymnt_log.adjusted_amount,
                        (
                            "pending"
                            if not fees_simulated
                            else "{:d}".format(int(pymnt_log.delegate_transaction_fee))
                        ),
                        (
                            "pending"
                            if not fees_simulated
                            else "{:d}".format(int(pymnt_log.delegator_transaction_fee))
                        ),
                        int(1) if pymnt_log.payable else int(0),
                        int(1) if pymnt_log.skipped else int(0),
                        pymnt_log.skippedatphase,
                        pymnt_log.desc,
                        pymnt_log.paymentaddress,
                        rt,
                    )
                )

        logger.info("Calculation report is created at '{}'".format(report_file))
