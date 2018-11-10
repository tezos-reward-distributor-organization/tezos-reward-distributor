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
        self.default = default
        if self.all_set(default):
            self.email_sender = EmailSender(default[HOST], int(default[PORT]), default[USER],
                                            default[PASS], default[SENDER])
        else:
            logger.info("If you want to send emails, populate email.ini file under current working directory.")

    def all_set(self, default):
        return default[USER] and default[PASS] and default[HOST] and default[PORT] and default[SENDER] and default[
            RECIPIENTS]

    def check_and_create_ini(self):
        if os.path.isfile(EMAIL_INI_PATH):
            return

        with open(EMAIL_INI_PATH, "w") as f:
            f.writelines(["[DEFAULT]\n", USER + NL, PASS + NL, HOST + NL, PORT + NL, SENDER + NL,
                          RECIPIENTS + NL])

    def send_payment_mail(self, cyle, payments_file, nb_failed):
        if not self.email_sender:
            return

        title = "Payment Report for Cycle {}".format(cyle)
        if nb_failed == 0: title + ", {} failed".format(nb_failed)

        self.email_sender.send(title, "Payment for cycle {} is completed. Report file is attached.".format(cyle),
                               self.default["recipients"], [payments_file])

        logger.debug("Report email sent for cycle {}.".format(cyle))

    def send_payment_mail_fail(self, cyle):
        if not self.email_sender:
            return

        self.email_sender.send("Payment Failed for Cycle {}".format(cyle),
                               "Payment for cycle {} failed.".format(cyle),
                               self.default["recipients"], [])

        logger.debug("Report email sent for cycle {}.".format(cyle))


if __name__ == '__main__':
    mm = EmailManager()
    mm.send_payment_mail(32, "D:\dev_root\\tezos-reward-distributer\\requirements.txt",0)
