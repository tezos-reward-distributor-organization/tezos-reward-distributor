import os

from util.dir_utils import payment_dir_c, payment_report_file_path, get_busy_file


#
# if there is a past payment evidence for a cycle, return evidence description. Else return None
def check_past_payment(payments_root, payment_cycle):
    payment_dir = payment_dir_c(payments_root, payment_cycle)

    # legacy payments
    if os.path.isdir(payment_dir):
        return "Payment directory for cycle {} is present. No payment will be run for the cycle. Check '{}'".format(
            payment_cycle, payment_dir
        )

    # new payments are reported to csv files
    payment_file = payment_report_file_path(payments_root, payment_cycle, 0)

    if os.path.isfile(payment_file):
        return "Payment report for cycle {} is present. No payment will be run for the cycle. Check '{}'".format(
            payment_cycle, payment_file
        )

    payment_file_failed = payment_report_file_path(payments_root, payment_cycle, 1)
    if os.path.isfile(payment_file_failed):
        return "Payment failed report for cycle {} is present. No payment will be run for the cycle. Check '{}'".format(
            payment_cycle, payment_file_failed
        )

    payment_file_failed_bush = get_busy_file(payment_file_failed)
    if os.path.isfile(payment_file_failed_bush):
        return "Busy payment failed report for cycle {} is present. No payment will be run for the cycle. Check '{}'".format(
            payment_cycle, payment_file_failed_bush
        )

    return None  # which means No past payment
