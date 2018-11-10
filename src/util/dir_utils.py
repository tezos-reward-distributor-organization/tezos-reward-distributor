import os

PAYMENT_DONE_DIR = "done"
PAYMENT_FAILED_DIR = "failed"
BUSY_FILE = ".BUSY"
PAYMENTS_ROOT_DIR = "payments"
CALCULATIONS_ROOT_DIR = "calculations"


def payment_report_file_path(pymnt_root, pymnt_cycle, nb_failed):
    return os.path.join(pymnt_root, PAYMENT_DONE_DIR if nb_failed == 0 else PAYMENT_FAILED_DIR,
                        str(pymnt_cycle) + '.csv')


def get_successful_payments_dir(pymnt_root, create=None):
    root_dir = os.path.join(pymnt_root, PAYMENT_DONE_DIR)
    if create: os.makedirs(root_dir)
    return root_dir


def get_failed_payments_dir(pymnt_root, create=None):
    root_dir = os.path.join(pymnt_root, PAYMENT_FAILED_DIR)
    if create: os.makedirs(root_dir)
    return root_dir


def get_busy_file(failed_payment_report_file):
    return failed_payment_report_file + BUSY_FILE


def get_payment_root(report_root, create=None):
    root_dir = os.path.join(report_root, PAYMENTS_ROOT_DIR)
    if create: os.makedirs(root_dir)
    return root_dir


def get_calculations_root(report_root, create=None):
    root_dir = os.path.join(report_root, CALCULATIONS_ROOT_DIR)
    if create: os.makedirs(root_dir)
    return root_dir


def get_calculation_report_file(calculations_root, cycle):
    return os.path.join(calculations_root, str(cycle)+".csv")


def reward_report_file_path(reward_root, pymnt_cycle):
    return os.path.join(reward_root, str(pymnt_cycle) + '.csv')


def payment_dir_c(pymnt_root, pymnt_cycle):
    return pymnt_root + "/" + str(pymnt_cycle)


def remove_busy_file(file):
    busy_file = get_busy_file(file)
    if os.path.isfile(busy_file):
        os.remove(busy_file)
        return True
    return False
