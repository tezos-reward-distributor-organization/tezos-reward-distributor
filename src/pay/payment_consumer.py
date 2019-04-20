import csv
import functools
import os
import threading
import time

import version
from Constants import EXIT_PAYMENT_TYPE
from calc.calculate_phase5 import CalculatePhase5
from calc.calculate_phase6 import CalculatePhase6
from emails.email_manager import EmailManager
from log_config import main_logger
from model.reward_log import cmp_by_type_balance, TYPE_MERGED, TYPE_FOUNDER, TYPE_OWNER, TYPE_DELEGATOR
from pay.batch_payer import BatchPayer
from stats.stats_pusblisher import stat_publish
from util.dir_utils import payment_report_file_path, get_busy_file

logger = main_logger
MUTEZ = 1e6


def count_and_log_failed(payment_logs, pymnt_cycle):
    nb_failed = 0
    for pymnt_itm in payment_logs:
        if pymnt_itm.paid:
            logger.info("Reward paid for cycle %s address %s amount %f tz type %s",
                        pymnt_cycle, pymnt_itm.address, pymnt_itm.amount, pymnt_itm.type)
        else:
            nb_failed = nb_failed + 1
            logger.warning("No Reward paid for cycle %s address %s amount %f tz: Reason client failed!",
                           pymnt_cycle, pymnt_itm.address, pymnt_itm.amount)
    return nb_failed


class PaymentConsumer(threading.Thread):
    def __init__(self, name, payments_dir, key_name, client_path, payments_queue, node_addr, wllt_clnt_mngr, args=None,
                 verbose=None, dry_run=None, delegator_pays_xfer_fee=True, dest_map=None, publish_stats=True):
        super(PaymentConsumer, self).__init__()

        self.dest_map = dest_map if dest_map else {}
        self.name = name
        self.payments_dir = payments_dir
        self.key_name = key_name
        self.client_path = client_path
        self.payments_queue = payments_queue
        self.node_addr = node_addr
        self.verbose = verbose
        self.dry_run = dry_run
        self.mm = EmailManager()
        self.wllt_clnt_mngr = wllt_clnt_mngr
        self.delegator_pays_xfer_fee = delegator_pays_xfer_fee
        self.publish_stats = publish_stats
        self.args = args

        logger.debug('Consumer "%s" created', self.name)

        return

    def run(self):
        while True:
            try:
                # 1-  wait until a reward is present
                payment_items = self.payments_queue.get(True)

                if payment_items[0].type == EXIT_PAYMENT_TYPE:
                    logger.debug("Exit signal received. Killing the thread...")
                    break

                # each log in the batch belongs to the same cycle
                pymnt_cycle = payment_items[0].cycle

                time.sleep(1)

                logger.info("Starting payments for cycle {}".format(pymnt_cycle))

                phase5 = CalculatePhase5(self.dest_map)
                payment_items, _ = phase5.calculate(payment_items, None)

                phase6 = CalculatePhase6(addr_dest_dict=self.dest_map)
                payment_items, _ = phase6.calculate(payment_items, None)

                # filter out non-payable items
                payment_items = [pi for pi in payment_items if pi.payable]

                payment_items.sort(key=functools.cmp_to_key(cmp_by_type_balance))

                batch_payer = BatchPayer(self.node_addr, self.key_name, self.wllt_clnt_mngr,
                                         self.delegator_pays_xfer_fee)

                # 3- do the payment
                payment_logs, total_attempts = batch_payer.pay(payment_items, self.verbose, dry_run=self.dry_run)

                # 4- count failed payments
                nb_failed = count_and_log_failed(payment_logs, pymnt_cycle)

                # 5- create payment report file
                report_file = self.create_payment_report(nb_failed, payment_logs, pymnt_cycle, total_attempts)

                # 6- upon successful payment, clean failure reports
                # note that failed payment reports are cleaned after creation of successful payment report
                if nb_failed == 0: self.clean_failed_payment_reports(pymnt_cycle)

                # 7- send email
                if not self.dry_run:
                    self.mm.send_payment_mail(pymnt_cycle, report_file, nb_failed)

            except Exception:
                logger.error("Error at reward payment", exc_info=True)

        logger.info("Consumer returning ...")

        return

    def clean_failed_payment_reports(self, payment_cycle):
        # 1- generate path of a assumed failure report file
        # if it exists, remove it
        failure_report_file = payment_report_file_path(self.payments_dir, payment_cycle, 1)
        if os.path.isfile(failure_report_file):
            os.remove(failure_report_file)
        # 2- generate path of a assumed busy failure report file
        # if it exists, remove it
        failure_report_busy_file = get_busy_file(failure_report_file)
        if os.path.isfile(failure_report_busy_file):
            os.remove(failure_report_busy_file)

    #
    # create report file
    def create_payment_report(self, nb_failed, payment_logs, payment_cycle, total_attempts):
        logger.info("Payment completed for {} addresses".format(len(payment_logs)))

        report_file = payment_report_file_path(self.payments_dir, payment_cycle, nb_failed)
        logger.info("Creating payment report (%s)", report_file)

        with open(report_file, "w") as f:
            csv_writer = csv.writer(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            csv_writer.writerow(["address", "type", "amount", "hash", "paid", "parent"])

            for pl in payment_logs:
                # write row to csv file
                csv_writer.writerow(
                    [pl.address, pl.type, pl.amount, pl.hash if pl.hash else "None",
                     "1" if pl.paid else "0", "None"])

                if pl.type == TYPE_MERGED and pl.parents:
                    for ppl in pl.parents:
                        csv_writer.writerow(
                            [ppl.address, ppl.type, ppl.amount, pl.hash if pl.hash else "None", "1" if pl.paid else "0",
                             pl.address])

                logger.info("Payment done for address %s type %s amount {:>8.2f} paid %s".format(pl.amount / MUTEZ),
                            pl.address, pl.type, pl.paid)

        if self.publish_stats and not self.dry_run:
            n_f_type = len([pl for pl in payment_logs if pl.type == TYPE_FOUNDER] + [p for pl in payment_logs if
                                                                                     pl.type == TYPE_MERGED for p in
                                                                                     pl.parents if
                                                                                     p.type == TYPE_FOUNDER])
            n_o_type = len([pl for pl in payment_logs if pl.type == TYPE_OWNER] + [p for pl in payment_logs if
                                                                                   pl.type == TYPE_MERGED for p in
                                                                                   pl.parents if p.type == TYPE_OWNER])
            n_d_type = len([pl for pl in payment_logs if pl.type == TYPE_DELEGATOR] + [p for pl in payment_logs if
                                                                                       pl.type == TYPE_MERGED for p in
                                                                                       pl.parents if
                                                                                       p.type == TYPE_DELEGATOR])
            n_m_type = len([pl for pl in payment_logs if pl.type == TYPE_MERGED])

            stats_dict = {}
            stats_dict['tot_amnt'] = sum([rl.amount for rl in payment_logs])
            stats_dict['nb_pay'] = len(payment_logs)
            stats_dict['nb_failed'] = nb_failed
            stats_dict['tot_attmpt'] = total_attempts
            stats_dict['nb_f'] = n_f_type
            stats_dict['nb_o'] = n_o_type
            stats_dict['nb_m'] = n_m_type
            stats_dict['nb_d'] = n_d_type
            stats_dict['cycle'] = payment_cycle
            stats_dict['m_fee'] = 1 if self.delegator_pays_xfer_fee else 0
            stats_dict['trdver'] = version.version

            if self.args:
                stats_dict['m_prov'] = 0 if self.args.reward_data_provider == 'tzscan' else 1
                m_relov = 0
                if self.args.release_override > 0:
                    m_relov = 1
                elif self.args.release_override < 0:
                    m_relov = -1
                stats_dict['m_relov'] = m_relov

            stat_publish(stats_dict)

        return report_file
