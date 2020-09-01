import configparser

import os

from emails.email_worker import EmailSender
from log_config import main_logger

NL = " = \n"

RECIPIENTS = 'recipients'
USER = "user"
PASS = "pass"
HOST = "smtp.host"
PORT = "smtp.port"
SENDER = "sender"
USE_SSL = "use.ssl"

EMAIL_INI_PATH = "./email.ini"

logger = main_logger


class EmailManager():
    def __init__(self):
        super(EmailManager, self).__init__()
        self.email_sender = None

        config = configparser.ConfigParser()
        self.check_and_create_ini()

        config.read(EMAIL_INI_PATH)
        default = config['DEFAULT']

        use_ssl = self.getUseSslOrFalse(default)

        self.default = default
        if self.all_set(default):
            self.email_sender = EmailSender(default[HOST], int(default[PORT]), default[USER], default[PASS],
                                            default[SENDER], use_ssl)
        else:
            logger.info("If you want to send emails, populate email.ini file under current working directory.")

    def getUseSslOrFalse(self, default):
        use_ssl = False
        if USE_SSL in default:
            use_ssl = default[USE_SSL]
        return use_ssl

    def all_set(self, default):
        return default[USER] and default[PASS] and default[HOST] and default[PORT] and default[SENDER] and default[
            RECIPIENTS]

    def check_and_create_ini(self):
        if os.path.isfile(EMAIL_INI_PATH):
            return

        with open(EMAIL_INI_PATH, "w") as f:
            f.writelines(["[DEFAULT]\n", USER + NL, PASS + NL, HOST + NL, PORT + NL, SENDER + NL,
                          RECIPIENTS + NL + USE_SSL + NL])

    def send_payment_mail(self, cycle, payments_file, nb_failed, nb_unknown, number_future_payable_cycles):
        if not self.email_sender:
            return

        title = "Payment Report for Cycle {}".format(cycle)
        if nb_failed > 0:
            title + ", {} failed".format(nb_failed)
        if nb_unknown > 0:
            title + ", {} final state not known".format(nb_unknown)

        self.email_sender.send(title, "Payment for cycle {} is completed. Report file is attached. "
                                      "The current payout account balance is expected to last for the next {} cycle(s)!".format(cycle, number_future_payable_cycles),
                               self.default["recipients"], [payments_file])

        logger.debug("Report email sent for cycle {}.".format(cycle))

    def warn_about_immediate_insufficient_funds(self, pay_addr, pay_amt, curr_bal):
        if not self.email_sender:
            return

        title = "FAILED payment because of insufficient funds"

        self.email_sender.send(title, "The last payment attempt failed because of an insufficient current balance of the payout address {}. Needed is at least {:,} mutez. Current balance is {:,} mutez. Please refund your payout address!!!".format(pay_addr, pay_amt, curr_bal),
                               self.default["recipients"], [])

        logger.info("Warning email about insufficient funds sent!")

    def warn_about_insufficient_funds_soon(self, pay_addr, pay_amt, curr_bal):
        if not self.email_sender:
            return

        title = "Payout address will soon run out of funds"

        self.email_sender.send(title, "The payout address {} will soon run out of funds and the current balance ({:,} mutez) might not be sufficient for the next cycle. Please refund your payout address!!!".format(pay_addr, curr_bal),
                               self.default["recipients"], [])

        logger.info("Warning email about insufficient funds sent!")
