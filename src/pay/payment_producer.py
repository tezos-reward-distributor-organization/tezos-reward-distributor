import _thread
import csv
import os
import threading
from datetime import datetime, timedelta
from time import sleep
from requests import ReadTimeout, ConnectTimeout
from Constants import MUTEZ, RunMode
from api.provider_factory import ProviderFactory
from calc.phased_payment_calculator import PhasedPaymentCalculator
from exception.api_provider import ApiProviderException
from log_config import main_logger, get_verbose_log_helper
from model.reward_log import RewardLog
from model.rules_model import RulesModel
from pay.double_payment_check import check_past_payment
from pay.payment_batch import PaymentBatch
from pay.payment_producer_abc import PaymentProducerABC
from pay.retry_producer import RetryProducer
from util.dir_utils import get_calculation_report_file, get_latest_report_file

logger = main_logger.getChild("payment_producer")

BOOTSTRAP_SLEEP = 8


class PaymentProducer(threading.Thread, PaymentProducerABC):
    def __init__(self, name, initial_payment_cycle, network_config, payments_dir, calculations_dir, run_mode,
                 service_fee_calc, release_override, payment_offset, baking_cfg, payments_queue, life_cycle,
                 dry_run, client_manager, node_url, reward_data_provider, node_url_public='', api_base_url=None,
                 retry_injected=False):
        super(PaymentProducer, self).__init__()

        self.rules_model = RulesModel(baking_cfg.get_excluded_set_tob(), baking_cfg.get_excluded_set_toe(),
                                      baking_cfg.get_excluded_set_tof(), baking_cfg.get_dest_map())
        self.baking_address = baking_cfg.get_baking_address()
        self.owners_map = baking_cfg.get_owners_map()
        self.founders_map = baking_cfg.get_founders_map()
        self.min_delegation_amt_in_mutez = baking_cfg.get_min_delegation_amount() * MUTEZ
        self.delegator_pays_xfer_fee = baking_cfg.get_delegator_pays_xfer_fee()
        self.provider_factory = ProviderFactory(reward_data_provider)
        self.name = name

        self.node_url = node_url
        self.client_manager = client_manager
        self.reward_api = self.provider_factory.newRewardApi(network_config, self.baking_address, self.node_url, node_url_public, api_base_url)
        self.block_api = self.provider_factory.newBlockApi(network_config, self.node_url, api_base_url)

        dexter_contracts_set = baking_cfg.get_contracts_set()
        if len(dexter_contracts_set) > 0 and not (self.reward_api.name == 'tzstats'):
            logger.warning("The Dexter functionality is currently only supported using tzstats."
                           "The contract address will be treated as a normal delegator.")
        else:
            self.reward_api.set_dexter_contracts_set(dexter_contracts_set)

        self.rewards_type = baking_cfg.get_rewards_type()
        self.fee_calc = service_fee_calc
        self.initial_payment_cycle = initial_payment_cycle

        if self.initial_payment_cycle is None:
            recent = get_latest_report_file(payments_dir)
            # if payment logs exists set initial cycle to following cycle
            # if payment logs does not exists, set initial cycle to 0, so that payment starts from last released rewards
            self.initial_payment_cycle = 0 if recent is None else int(recent) + 1

        logger.info("initial_cycle set to {}".format(self.initial_payment_cycle))

        self.nw_config = network_config
        self.payments_root = payments_dir
        self.calculations_dir = calculations_dir
        self.run_mode = run_mode
        self.exiting = False

        self.release_override = release_override
        self.payment_offset = payment_offset
        self.payments_queue = payments_queue
        self.life_cycle = life_cycle
        self.dry_run = dry_run

        self.payment_calc = PhasedPaymentCalculator(self.founders_map, self.owners_map, self.fee_calc,
                                                    self.min_delegation_amt_in_mutez, self.rules_model)

        self.retry_fail_thread = threading.Thread(target=self.retry_fail_run, name=self.name + "_retry_fail")
        self.retry_fail_event = threading.Event()
        self.retry_injected = retry_injected

        self.retry_producer = RetryProducer(self.payments_queue, self.reward_api, self, self.payments_root, self.retry_injected)

        logger.info('Producer "{}" started'.format(self.name))

    def exit(self):
        if not self.exiting:
            self.payments_queue.put(PaymentBatch(self, 0, [self.create_exit_payment()]))
            self.exiting = True

            if self.life_cycle.is_running() and threading.current_thread() is not threading.main_thread():
                _thread.interrupt_main()

            if self.retry_fail_event:
                self.retry_fail_event.set()

    def retry_fail_run(self):
        logger.info('Retry Fail thread "{}" started'.format(self.retry_fail_thread.name))

        sleep(60)  # producer thread already tried once, wait for next try

        while not self.exiting and self.life_cycle.is_running():
            self.retry_producer.retry_failed_payments()

            try:
                # prepare to wait on event
                self.retry_fail_event.clear()

                # this will either return with timeout or set from parent producer thread
                self.retry_fail_event.wait(60 * 60)  # 1 hour
            except RuntimeError:
                pass

    def run(self):
        # call first retry if not in onetime mode.
        # retry_failed script is more suitable for one time cases.
        if not self.run_mode == RunMode.ONETIME:
            self.retry_producer.retry_failed_payments()

            if self.run_mode == RunMode.RETRY_FAILED:
                sleep(5)
                self.exit()
                return

        # first retry is done by producer thread, start retry thread for further retries
        if self.run_mode == RunMode.FOREVER:
            self.retry_fail_thread.start()

        try:
            current_cycle = self.block_api.get_current_cycle()
            pymnt_cycle = self.initial_payment_cycle
        except ApiProviderException as a:
            logger.error("Unable to fetch current cycle, {:s}. Exiting.".format(str(a)))
            self.exit()
            return

        # if non-positive initial_payment_cycle, set initial_payment_cycle to
        # 'current cycle - abs(initial_cycle) - (NB_FREEZE_CYCLE+1)'
        if self.initial_payment_cycle <= 0:
            pymnt_cycle = current_cycle - abs(self.initial_payment_cycle) - (self.nw_config['NB_FREEZE_CYCLE'] + 1)
            logger.debug("Payment cycle is set to {}".format(pymnt_cycle))

        get_verbose_log_helper().reset(pymnt_cycle)

        while not self.exiting and self.life_cycle.is_running():

            # take a breath
            sleep(5)

            try:

                # Check if local node is bootstrapped; sleep if needed; restart loop
                if not self.node_is_bootstrapped():
                    logger.info("Local node, {}, is not in sync with the Tezos network. Will sleep for {} blocks and check again." .format(self.node_url, BOOTSTRAP_SLEEP))
                    self.wait_for_blocks(BOOTSTRAP_SLEEP)
                    continue

                # Local node is ready
                current_level = self.block_api.get_current_level()
                current_cycle = self.block_api.level_to_cycle(current_level)
                level_in_cycle = self.block_api.level_in_cycle(current_level)

                # create reports dir
                if self.calculations_dir and not os.path.exists(self.calculations_dir):
                    os.makedirs(self.calculations_dir)

                logger.debug("Checking for pending payments : payment_cycle <= current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override")
                logger.info("Checking for pending payments : checking {} <= {} - ({} + 1) - {}".format(pymnt_cycle, current_cycle, self.nw_config['NB_FREEZE_CYCLE'], self.release_override))

                # payments should not pass beyond last released reward cycle
                if pymnt_cycle <= current_cycle - (self.nw_config['NB_FREEZE_CYCLE'] + 1) - self.release_override:
                    if not self.payments_queue.full():

                        # Paying upcoming cycles (-R in [-6, -11] )
                        if pymnt_cycle >= current_cycle:
                            logger.warn("Please note that you are doing payouts for future rewards!!! These rewards are not earned yet, they are an estimation.")
                            if not self.rewards_type.isExpected():
                                logger.error("For future rewards payout, you must configure the payout type to 'Expected', see documentation")
                                self.exit()
                                break

                        # Paying cycles with frozen rewards (-R in [-1, -5] )
                        elif pymnt_cycle >= current_cycle - self.nw_config['NB_FREEZE_CYCLE']:
                            logger.warn("Please note that you are doing payouts for frozen rewards!!!")
                            if (not self.rewards_type.isExpected()) and self.reward_api.name == 'RPC':
                                logger.error("Paying out frozen rewards with Node RPC API and rewards type 'Ideal' or 'Actual' is unsupported, you must use TzKT or tzstats API")
                                self.exit()
                                break

                        # Payment cycle with unfrozen rewards (-R >= 0)
                        else:
                            if self.rewards_type.isIdeal() and self.reward_api.name == 'RPC':
                                logger.error("Paying out rewards of type 'Ideal' with Node RPC API is unsupported, you must use TzKT or tzstats API")
                                self.exit()
                                break

                        # If user wants to offset payments within a cycle, check here
                        if level_in_cycle < self.payment_offset:
                            wait_offset_blocks = self.payment_offset - level_in_cycle
                            logger.info("Current level within the cycle is {}; Requested offset is {}; Waiting for {} more blocks." .format(level_in_cycle, self.payment_offset, wait_offset_blocks))
                            self.wait_for_blocks(wait_offset_blocks)
                            continue  # Break/Repeat loop

                        else:
                            result = self.try_to_pay(pymnt_cycle, self.rewards_type)

                        if result:
                            # single run is done. Do not continue.
                            if self.run_mode == RunMode.ONETIME:
                                logger.info("Run mode ONETIME satisfied. Terminating ...")
                                self.exit()
                                break
                            else:
                                pymnt_cycle = pymnt_cycle + 1
                                get_verbose_log_helper().reset(pymnt_cycle)

                    # end of queue size check
                    else:
                        logger.debug("Wait a few minutes, queue is full")
                        # wait a few minutes to let payments finish
                        sleep(60 * 3)

                # end of payment cycle check
                else:
                    logger.info("No pending payments for cycle {}, current cycle is {}".format(pymnt_cycle, current_cycle))

                    # pending payments done. Do not wait any more.
                    if self.run_mode == RunMode.PENDING:
                        logger.info("Run mode PENDING satisfied. Terminating ...")
                        self.exit()
                        break

                    sleep(10)

                    # calculate number of blocks until end of current cycle
                    nb_blocks_remaining = (current_cycle + 1) * self.nw_config['BLOCKS_PER_CYCLE'] - current_level

                    # plus offset. cycle beginnings may be busy, move payments forward
                    nb_blocks_remaining = nb_blocks_remaining + self.payment_offset

                    logger.debug("Waiting until next cycle; {} blocks remaining".format(nb_blocks_remaining))

                    # wait until current cycle ends
                    self.wait_for_blocks(nb_blocks_remaining)

            except (ApiProviderException, ReadTimeout, ConnectTimeout) as e:
                logger.debug("{:s} error at payment producer loop: '{:s}'".format(self.reward_api.name, str(e)), exc_info=True)
                logger.error("{:s} error at payment producer loop: '{:s}', will try again.".format(
                             self.reward_api.name, str(e)))

            except Exception as e:
                logger.debug("Unknown error in payment producer loop: {:s}".format(str(e)), exc_info=True)
                logger.error("Unknown error in payment producer loop: {:s}, will try again.".format(str(e)))

        # end of endless loop
        logger.info("Producer returning ...")

        # ensure consumer exits
        self.exit()

        return

    def try_to_pay(self, pymnt_cycle, rewards_type):
        try:
            logger.info("Payment cycle is " + str(pymnt_cycle))

            # 0- check for past payment evidence for current cycle
            past_payment_state = check_past_payment(self.payments_root, pymnt_cycle)

            if not self.dry_run and past_payment_state:
                logger.warn(past_payment_state)
                return True

            # 1- get reward data
            if rewards_type.isExpected():
                logger.info("Using expected rewards for payouts calculations")
            elif rewards_type.isActual():
                logger.info("Using actual rewards for payouts calculations")
            elif rewards_type.isIdeal():
                logger.info("Using ideal rewards for payouts calculations")

            reward_model = self.reward_api.get_rewards_for_cycle_map(pymnt_cycle, rewards_type)

            # 2- calculate rewards
            reward_logs, total_amount = self.payment_calc.calculate(reward_model)

            # 3- set cycle info
            for rl in reward_logs:
                rl.cycle = pymnt_cycle
            total_amount_to_pay = sum([rl.amount for rl in reward_logs if rl.payable])

            # 4- if total_rewards > 0, proceed with payment
            if total_amount_to_pay > 0:
                report_file_path = get_calculation_report_file(self.calculations_dir, pymnt_cycle)

                # 5- send to payment consumer
                self.payments_queue.put(PaymentBatch(self, pymnt_cycle, reward_logs))

                # logger.info("Total payment amount is {:,} mutez. %s".format(total_amount_to_pay),
                #            "" if self.delegator_pays_xfer_fee else "(Transfer fee is not included)")

                logger.debug("Creating calculation report (%s)", report_file_path)

                sleep(5.0)

                # 6- create calculations report file. This file contains calculations details
                self.create_calculations_report(reward_logs, report_file_path, total_amount, rewards_type)

                # 7- processing of cycle is done
                logger.info("Reward creation is done for cycle {}, created {} rewards.".format(pymnt_cycle, len(reward_logs)))

            elif total_amount_to_pay == 0:
                logger.info("Total payment amount is 0. Nothing to pay!")

        except ApiProviderException as a:
            logger.error("[try_to_pay] API provider error {:s}".format(str(a)))
            raise a from a
        except Exception as e:
            logger.error("[try_to_pay] Generic exception {:s}".format(str(e)))
            raise e from e

        # Either succeeded or raised exception
        return True

    def wait_for_blocks(self, nb_blocks_remaining):
        for x in range(nb_blocks_remaining):
            sleep(self.nw_config['BLOCK_TIME_IN_SEC'])

            # if shutting down, exit
            if not self.life_cycle.is_running():
                self.exit()
                break

    def node_is_bootstrapped(self):
        # Get RPC node's (-A) bootstrap time. If bootstrap time + 2 minutes is
        # before local time, node is not bootstrapped.
        #
        # clnt_mngr is a super class of SimpleClientManager which interfaces
        # with the tezos-node used for txn forging/signing/injection. This is the
        # node which we need to determine bootstrapped state
        try:
            boot_time = self.client_manager.get_bootstrapped()
            utc_time = datetime.utcnow()
            if (boot_time + timedelta(minutes=2)) < utc_time:
                logger.info("Current time is '{}', latest block of local node is '{}'."
                            .format(utc_time, boot_time))
                return False
        except ValueError:
            logger.error("Unable to determine local node's bootstrap status. Continuing...")
        return True

    def create_calculations_report(self, payment_logs, report_file_path, total_rewards, rewards_type):

        if rewards_type.isExpected():
            rt = "E"
        elif rewards_type.isActual():
            rt = "A"
        elif rewards_type.isIdeal():
            rt = "I"

        # Open reports file and write; auto-closes file
        with open(report_file_path, 'w', newline='') as f:

            writer = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            # write headers and total rewards
            writer.writerow(
                ["address", "type", "staked_balance", "current_balance", "ratio", "fee_ratio", "amount", "fee_amount", "fee_rate", "payable",
                 "skipped", "atphase", "desc", "payment_address", "rewards_type"])

            # First row is for the baker
            writer.writerow([self.baking_address, "B", sum([pl.staking_balance for pl in payment_logs]),
                             "{0:f}".format(1.0),
                             "{0:f}".format(1.0),
                             "{0:f}".format(0.0),
                             "{0:f}".format(total_rewards),
                             "{0:f}".format(0.0),
                             "{0:f}".format(0.0),
                             "0", "0", "-1", "Baker",
                             "None", rt
                             ])

            for pymnt_log in payment_logs:
                # write row to csv file
                array = [pymnt_log.address, pymnt_log.type, pymnt_log.staking_balance, pymnt_log.current_balance,
                         "{0:.10f}".format(pymnt_log.ratio),
                         "{0:.10f}".format(pymnt_log.service_fee_ratio),
                         "{0:f}".format(pymnt_log.amount),
                         "{0:f}".format(pymnt_log.service_fee_amount),
                         "{0:f}".format(pymnt_log.service_fee_rate),
                         "1" if pymnt_log.payable else "0", "1" if pymnt_log.skipped else "0",
                         pymnt_log.skippedatphase if pymnt_log.skipped else "-1",
                         pymnt_log.desc if pymnt_log.desc else "None",
                         pymnt_log.paymentaddress, rt]
                writer.writerow(array)

                logger.debug("Reward created for {:s} type: {:s}, stake bal: {:>10.2f}, cur bal: {:>10.2f}, ratio: {:.6f}, fee_ratio: {:.6f}, "
                             "amount: {:>10.6f}, fee_amount: {:>4.6f}, fee_rate: {:.2f}, payable: {:s}, skipped: {:s}, at-phase: {:d}, "
                             "desc: {:s}, pay_addr: {:s}, type: {:s}"
                             .format(pymnt_log.address, pymnt_log.type,
                                     pymnt_log.staking_balance / MUTEZ, pymnt_log.current_balance / MUTEZ,
                                     pymnt_log.ratio, pymnt_log.service_fee_ratio,
                                     pymnt_log.amount / MUTEZ, pymnt_log.service_fee_amount / MUTEZ,
                                     pymnt_log.service_fee_rate, "Y" if pymnt_log.payable else "N",
                                     "Y" if pymnt_log.skipped else "N", pymnt_log.skippedatphase,
                                     pymnt_log.desc, pymnt_log.paymentaddress, rt))

        logger.info("Calculation report is created at '{}'".format(report_file_path))

    @staticmethod
    def create_exit_payment():
        return RewardLog.ExitInstance()

    def notify_retry_fail_thread(self):
        self.retry_fail_event.set()

    # upon success retry failed payments if present
    # success may indicate what went wrong in past is fixed.
    def on_success(self, pymnt_batch):
        self.notify_retry_fail_thread()

    def on_fail(self, pymnt_batch):
        pass
