import sys
import sqlite3
from Constants import MUTEZ
from log_config import main_logger

logger = main_logger

class ReportStorage:


    def __init__(self, _storage):

        logger.info("ReportStorage - Init")

        self._storage = _storage
        self.__create_tables()


    def get_recent_cycle(self):
        r_cycle = None
        with self._storage as dbh:
            try:
                r_sql = "SELECT MAX(cycle) FROM payments WHERE paid > 0"
                cur = dbh.execute(r_sql)
                r_cycle = cur.fetchone()[0]  # Returns a tuple; Just need 1st element
            except sqlite3.Error as e:
                raise ReportStorageException("Unable to get most recent cycle: {}".format(e)) from e
        return r_cycle


    def get_failed_payment_cycles(self):
        cycles = []
        with self._storage as dbh:
            try:
                fetch_sql = "SELECT DISTINCT cycle FROM payments WHERE paid = 0"
                cur = dbh.execute(fetch_sql)
                cycles = cur.fetchall()
            except sqlite3.Error as e:
                raise ReportStorageException("Unable to get failed payment cycles: {}".format(e)) from e
            except:
                raise
        return cycles


    def get_failed_payments(self, cycle):
        payments = []
        with self._storage as dbh:
            try:
                fetch_sql = "SELECT * FROM payments WHERE paid = 0 AND cycle = ?"
                cur = dbh.execute(fetch_sql, (cycle,))
                payments = cur.fetchall()
            except sqlite3.Error as e:
                raise ReportStorageException("Unable to get failed payments: {}".format(e)) from e
            except:
                raise
        return payments


    def check_past_payment(self, cycle):

        # Just need counts of successful, and failed payments for this cycle.
        # This will determine if main producer should ignore/skip this cycle.
        nb_fail = 0
        nb_success = 0

        with self._storage as dbh:
            try:
                f_sql = "SELECT COUNT(*), paid FROM payments WHERE cycle = ? GROUP BY paid"

                # 0th = count, 1st = paid
                for r in dbh.execute(f_sql, (cycle,)):
                    if r[1] > 0:
                        nb_success += r[0]
                    elif r[1] == 0:
                        nb_fail += r[0]
                    else:
                        logger.info("Unknown past payment state found for cycle {}: '{}'".format(cycle, r))

            except sqlite3.Error as e:
                raise ReportStorageException("Unable to get failed payments: {}".format(e)) from e
            except:
                raise

        return nb_fail, nb_success

    def save_payment_report(self, cycle, payment_logs):

        #
        # We use REPLACE here so that if a payment initially fails, but then succeeds on
        # retry_fail, we update/replace the original row with the new one, which should
        # be the same data except for the 'paid' column now indicates success.
        #
        insert_sql = """REPLACE INTO payments (cycle, address, type, amount, staked_balance,
            current_balance, opHash, paid) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""

        with self._storage as dbh:
            try:
                logger.debug("save_payment_report - BEGIN")

                for pl in payment_logs:

                    data_t = (cycle, pl.address, pl.type, pl.amount, pl.staking_balance,
                        pl.current_balance, pl.hash, pl.paid.value)
                    dbh.execute(insert_sql, data_t)

                logger.debug("save_payment_report - COMMIT")

            except sqlite3.Error as e:
                raise ReportStorageException("Unable to save payment report to database: {}".format(e)) from e
            except:
                raise


    def save_calculations_report(self, baker_address, cycle, reward_logs, total_reward_amount):

        insert_sql = """REPLACE INTO calculations (
            cycle, address, payment_address, type, staked_balance, current_balance, ratio, fee_ratio, amount,
            fee_amount, fee_rate, payable, skipped, atphase, desc) VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""

        with self._storage as dbh:

            try:
                logger.debug("save_calculations_report - BEGIN")

                # Baker report
                baker_t = (cycle, baker_address, baker_address, "B",
                    sum([rl.staking_balance for rl in reward_logs]), 1.0, 1.0, 0.0,
                    total_reward_amount, 0.0, 0.0, "0", "0", "-1", "Baker")

                dbh.execute(insert_sql, baker_t)

                # Loop over RewardLogs and insert to DB
                for rl in reward_logs:

                    # Create tuple for prepared statement
                    data_t = (cycle, rl.address, rl.paymentaddress, rl.type, rl.staking_balance, rl.current_balance,
                        rl.ratio, rl.service_fee_ratio, rl.amount, rl.service_fee_amount, rl.service_fee_rate,
                        1 if rl.payable else 0, 1 if rl.skipped else 0,
                        rl.skippedatphase if rl.skipped else -1, rl.desc if rl.desc else "None")

                    dbh.execute(insert_sql, data_t)

                    logger.debug("DB reward: {:s} -> {:s} ({:s}), Staked: {:>10.2f}, Current: {:>10.2f}, Ratio: {:.6f}, "
                        "fee_ratio: {:.6f}, amount: {:>10.6f}, fee_amount: {:>4.6f}, fee_rate: {:.2f}, payable: {:b}, "
                        "skipped: {:b}, at-phase: {:d}, desc: {:s}".format(rl.address, rl.paymentaddress, rl.type,
                        rl.staking_balance / MUTEZ, rl.current_balance / MUTEZ,
                        rl.ratio, rl.service_fee_ratio, rl.amount / MUTEZ, rl.service_fee_amount / MUTEZ,
                        rl.service_fee_rate, rl.payable, rl.skipped, rl.skippedatphase, rl.desc))

                logger.debug("save_calculations_report - COMMIT")

            except sqlite3.Error as e:
                raise ReportStorageException("Unable to save calculations report to database: {}".format(e)) from e
            except:
                raise


    def __create_tables(self):

        with self._storage as dbh:
            try:
                dbh.execute("""CREATE TABLE IF NOT EXISTS calculations (
                    cycle integer, address text, payment_address text, type text, staked_balance real,
                    current_balance real, ratio real, fee_ratio real, amount real, fee_amount real,
                    fee_rate real, payable numeric, skipped numeric, atphase integer, desc text)""")

                dbh.execute("""CREATE TABLE IF NOT EXISTS payments (
                    cycle integer, address text, type text, amount real, staked_balance real,
                    current_balance real, opHash text, paid integer)""")

                dbh.execute("CREATE UNIQUE INDEX IF NOT EXISTS uk_p_c_a ON payments (cycle, address)")
                dbh.execute("CREATE UNIQUE INDEX IF NOT EXISTS uk_c_c_a ON calculations (cycle, address)")

            except sqlite3.Error as e:
                raise ReportStorageException("Unable to create tables: {}".format(e)) from e
            except:
                raise

class ReportStorageException(Exception):
    pass
