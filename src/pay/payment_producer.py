import os
import platform
import signal
import threading
from datetime import datetime, timedelta
from _decimal import ROUND_HALF_DOWN, Decimal
from time import sleep
from requests import ReadTimeout, ConnectTimeout
from Constants import MUTEZ_PER_TEZ, RunMode, RewardsType
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
from util.csv_calculation_file_parser import CsvCalculationFileParser
from util.dir_utils import get_calculation_report_file_path
from util.disk_is_full import disk_is_full
from util.exit_program import exit_program, ExitCode

logger = main_logger.getChild("payment_producer")

BOOTSTRAP_SLEEP = 4


class PaymentProducer(threading.Thread, PaymentProducerABC):
    def __init__(
        self,
        name,
        initial_payment_cycle,
        network_config,
        payments_dir,
        calculations_dir,
        run_mode,
        service_fee_calc,
        release_override,
        payment_offset,
        baking_cfg,
        payments_queue,
        life_cycle,
        dry_run,
        client_manager,
        node_url,
        reward_data_provider,
        node_url_public="",
        api_base_url=None,
        retry_injected=False,
    ):
        super(PaymentProducer, self).__init__()
        self.event = threading.Event()
        self.rules_model = RulesModel(
            baking_cfg.get_excluded_set_tob(),
            baking_cfg.get_excluded_set_toe(),
            baking_cfg.get_excluded_set_tof(),
            baking_cfg.get_dest_map(),
        )
        self.baking_address = baking_cfg.get_baking_address()
        self.owners_map = baking_cfg.get_owners_map()
        self.founders_map = baking_cfg.get_founders_map()
        self.min_delegation_amt_in_mutez = int(
            baking_cfg.get_min_delegation_amount() * MUTEZ_PER_TEZ
        )
        self.delegator_pays_xfer_fee = baking_cfg.get_delegator_pays_xfer_fee()
        self.provider_factory = ProviderFactory(reward_data_provider)
        self.name = name
        self.min_payment_amt_in_mutez = int(
            baking_cfg.get_min_payment_amount() * MUTEZ_PER_TEZ
        )

        self.node_url = node_url
        self.client_manager = client_manager
        self.tzpro_api_key = baking_cfg.get_tzpro_api_key()
        self.reward_api = self.provider_factory.newRewardApi(
            network_config,
            self.baking_address,
            self.node_url,
            node_url_public,
            api_base_url,
            self.tzpro_api_key,
        )
        self.block_api = self.provider_factory.newBlockApi(
            network_config,
            self.node_url,
            api_base_url,
            self.tzpro_api_key,
        )

        dexter_contracts_set = baking_cfg.get_contracts_set()
        if len(dexter_contracts_set) > 0 and not (self.reward_api.name == "tzpro"):
            logger.warning(
                "The Dexter functionality is currently only supported using tzpro."
                "The contract address will be treated as a normal delegator."
            )
        else:
            self.reward_api.set_dexter_contracts_set(dexter_contracts_set)

        self.rewards_type = baking_cfg.get_rewards_type()
        self.pay_denunciation_rewards = baking_cfg.get_pay_denunciation_rewards()
        self.fee_calc = service_fee_calc
        self.initial_payment_cycle = initial_payment_cycle

        logger.info("Initial cycle set to {}".format(self.initial_payment_cycle))

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
        self.consumer_failure = False

        self.payment_calc = PhasedPaymentCalculator(
            self.founders_map,
            self.owners_map,
            self.fee_calc,
            self.min_delegation_amt_in_mutez,
            self.min_payment_amt_in_mutez,
            self.rules_model,
            self.reward_api,
        )

        self.retry_fail_thread = threading.Thread(
            target=self.retry_fail_run, name=self.name + "_retry_fail"
        )
        self.retry_fail_event = threading.Event()
        self.retry_injected = retry_injected

        self.retry_producer = RetryProducer(
            self.payments_queue,
            self.reward_api,
            self,
            self.payments_root,
            self.initial_payment_cycle,
            self.retry_injected,
        )

        logger.debug('Producer "{}" started'.format(self.name))

    def exit(self, exit_code):
        if not self.exiting:
            self.payments_queue.put(PaymentBatch(self, 0, [self.create_exit_payment()]))
            self.exiting = True

            if (
                self.life_cycle.is_running()
                and threading.current_thread() is not threading.main_thread()
            ):
                if platform.system() == "Windows":
                    abnormal_signal = signal.SIGTERM
                    normal_signal = signal.SIGTERM
                else:
                    # This will propagate the exit status to main process on linux.
                    abnormal_signal = signal.SIGUSR2
                    normal_signal = signal.SIGUSR1
                if self.consumer_failure:
                    os.kill(os.getpid(), abnormal_signal)
                    logger.debug(
                        "Payment failure, sending abnormal kill signal to main thread."
                    )
                elif exit_code != ExitCode.SUCCESS:
                    os.kill(os.getpid(), abnormal_signal)
                    logger.debug(
                        "Producer failure, sending abnormal kill signal to main thread."
                    )
                else:
                    os.kill(os.getpid(), normal_signal)
                    logger.debug("Sending normal kill signal.")
                exit_program(
                    exit_code,
                    "TRD Exit triggered by producer",
                )
            if self.retry_fail_event:
                self.retry_fail_event.set()

    def retry_fail_run(self):
        logger.debug(
            'Retry Fail thread "{}" started'.format(self.retry_fail_thread.name)
        )

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
                self.exit(ExitCode.RETRY_FAILED)
                return

        # first retry is done by producer thread, start retry thread for further retries
        if self.run_mode == RunMode.FOREVER:
            self.retry_fail_thread.start()

        try:
            (
                current_cycle,
                current_level,
            ) = self.block_api.get_current_cycle_and_level()
        except ApiProviderException as a:
            logger.error(
                "Unable to fetch current cycle from provider {:s}, {:s}. Exiting.".format(
                    str(self.provider_factory.provider), str(a)
                )
            )
            self.exit(ExitCode.PROVIDER_ERROR)
            return

        # if initial_payment_cycle has the default value of -1 resulting in the last released cycle
        if self.initial_payment_cycle == -1:
            pymnt_cycle = current_cycle - 1 - self.release_override
            if pymnt_cycle < 0:
                logger.error(
                    "Payment cycle cannot be < 0 but configuration results to {}".format(
                        pymnt_cycle
                    )
                )
            else:
                logger.debug(
                    "Payment cycle is set to last released cycle {}".format(pymnt_cycle)
                )
        else:
            pymnt_cycle = self.initial_payment_cycle

        get_verbose_log_helper().reset(pymnt_cycle)

        while not self.exiting and self.life_cycle.is_running():
            # take a breath
            sleep(5)

            try:
                # Exit if disk is full
                # https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/504
                if disk_is_full():
                    self.exit(ExitCode.NO_SPACE)
                    break

                # Check if local node is bootstrapped; sleep if needed; restart loop
                if not self.node_is_bootstrapped():
                    logger.info(
                        "Local node {} is not in sync with the Tezos network. Will sleep for {} blocks and check again.".format(
                            self.node_url, BOOTSTRAP_SLEEP
                        )
                    )
                    self.wait_for_blocks(BOOTSTRAP_SLEEP)
                    continue

                # Local node is ready
                (
                    current_cycle,
                    current_level,
                ) = self.block_api.get_current_cycle_and_level()
                level_in_cycle = self.block_api.level_in_cycle(current_level)

                # create reports dir
                if self.calculations_dir and not os.path.exists(self.calculations_dir):
                    os.makedirs(self.calculations_dir)

                logger.debug(
                    "Checking for pending payments: payment_cycle <= current_cycle - 1 - self.release_override"
                )
                logger.info(
                    "Checking for pending payments: checking {} <= {} - 1 - {}".format(
                        pymnt_cycle,
                        current_cycle,
                        self.release_override,
                    )
                )

                # payments should not pass beyond last released reward cycle
                if pymnt_cycle <= current_cycle - 1 - self.release_override:
                    if not self.payments_queue.full():
                        # Paying upcoming cycles (--adjusted_early_payouts is provided )
                        if pymnt_cycle >= current_cycle:
                            logger.warn(
                                "Please note that you are doing payouts for future rewards!!! These rewards are not earned yet, they are an estimation."
                            )
                            logger.warn(
                                "TRD will attempt to adjust the amount after the cycle runs, but it may not work."
                            )

                        # If user wants to offset payments within a cycle, check here
                        if level_in_cycle < self.payment_offset:
                            wait_offset_blocks = self.payment_offset - level_in_cycle
                            wait_offset_minutes = (
                                wait_offset_blocks
                                * self.nw_config["MINIMAL_BLOCK_DELAY"]
                            ) / 60
                            logger.info(
                                "Current level within the cycle is {}; Requested offset is {}; Waiting for {} more blocks (~{} minutes)".format(
                                    level_in_cycle,
                                    self.payment_offset,
                                    wait_offset_blocks,
                                    wait_offset_minutes,
                                )
                            )
                            self.wait_for_blocks(wait_offset_blocks)
                            continue  # Break/Repeat loop

                        else:
                            result = self.try_to_pay(
                                pymnt_cycle,
                                self.rewards_type,
                                self.nw_config,
                                current_cycle,
                            )

                        if result:
                            # single run is done. Do not continue.
                            if self.run_mode == RunMode.ONETIME:
                                logger.info(
                                    "Run mode ONETIME satisfied. Terminating..."
                                )
                                self.exit(ExitCode.SUCCESS)
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
                    logger.info(
                        "No pending payments for cycle {}, current cycle is {}".format(
                            pymnt_cycle, current_cycle
                        )
                    )

                    # pending payments done. Do not wait any more.
                    if self.run_mode == RunMode.PENDING:
                        logger.info("Run mode PENDING satisfied. Terminating...")
                        self.exit(ExitCode.SUCCESS)
                        break

                    sleep(10)

                    # calculate number of blocks until end of current cycle plus user-defined offset
                    nb_blocks_remaining = (
                        self.nw_config["BLOCKS_PER_CYCLE"]
                        - level_in_cycle
                        + self.payment_offset
                    )
                    logger.debug(
                        "Waiting until next cycle; {} blocks remaining".format(
                            nb_blocks_remaining
                        )
                    )

                    # wait until current cycle ends
                    self.wait_for_blocks(nb_blocks_remaining)

            except (ApiProviderException, ReadTimeout, ConnectTimeout) as e:
                logger.debug(
                    "{:s} error at payment producer loop: '{:s}'".format(
                        self.reward_api.name, str(e)
                    ),
                    exc_info=True,
                )
                logger.error(
                    "{:s} error at payment producer loop: '{:s}', will try again.".format(
                        self.reward_api.name, str(e)
                    )
                )

            except Exception as e:
                logger.debug(
                    "Unknown error in payment producer loop: {:s}".format(str(e)),
                    exc_info=True,
                )
                logger.error(
                    "Unknown error in payment producer loop: {:s}, will try again.".format(
                        str(e)
                    )
                )

        # end of endless loop
        logger.debug("Producer returning...")

        # ensure consumer exits
        self.exit(ExitCode.SUCCESS)

        return

    def stop(self):
        self.exit(ExitCode.SUCCESS)
        self.event.set()

    def compute_rewards(
        self, pymnt_cycle, computation_type, network_config, adjustments={}
    ):
        """
        Compute total rewards based on computation type and policy, then
        calls payment_call.calculate to calculate rewards per delegator.

        :param pymnt_cycle: the cycle for which rewards are being calculated
        :param computation_type: calculate estimated, actual or ideal rewards
        :param network_config: configuration of the current tezos network, needed to calc rewards.
        :param adjustments: a map of adjustments per address. We add to amount to compute adjusted_amount
        :return: rewards per delegator (reward logs) and total amount
        """
        # does calculation report file already exist for this cycle?

        logger.info("Computing rewards for cycle {:s}.".format(str(pymnt_cycle)))
        reward_model = self.reward_api.get_rewards_for_cycle_map(
            pymnt_cycle, computation_type
        )
        if computation_type.isEstimated():
            logger.info("Using estimated rewards for payouts calculations")
            block_reward = network_config["BLOCK_REWARD"]
            total_estimated_block_reward = reward_model.num_baking_rights * block_reward
            total_estimated_endorsement_reward = (
                reward_model.potential_endorsement_rewards
            )
            reward_model.computed_reward_amount = (
                total_estimated_block_reward + total_estimated_endorsement_reward
            )
        elif computation_type.isActual():
            logger.info("Using actual rewards for payouts calculations")
            if self.pay_denunciation_rewards:
                reward_model.computed_reward_amount = reward_model.total_reward_amount
            else:
                # omit denunciation rewards
                reward_model.computed_reward_amount = (
                    reward_model.rewards_and_fees - reward_model.equivocation_losses
                )
        elif computation_type.isIdeal():
            logger.info("Using ideal rewards for payouts calculations")
            if self.pay_denunciation_rewards:
                reward_model.computed_reward_amount = (
                    reward_model.total_reward_amount + reward_model.offline_losses
                )
            else:
                # omit denunciation rewards and double baking loss
                reward_model.computed_reward_amount = (
                    reward_model.rewards_and_fees + reward_model.offline_losses
                )

        # 3- calculate rewards for delegators
        return self.payment_calc.calculate(reward_model, adjustments)

    def recompute_rewards(self, completed_cycle, computation_type, network_config):
        """
        In case of early payout, the payout is already done when the cycle runs.
        After a cycle has run, we redo the computations. If we find overpayemnt
        (overestimate) or underpayment (negative overestimate), we record it in the
        calculation report csv file and return an adjustment map.

        :param completed_cycle: the cycle for which rewards are being recalculated
        :param computation_type: calculate estimated, actual or ideal rewards
        :param network_config: configuration of the current tezos network, needed to calc rewards.
        :return: adjustments map showing negative of overestimates per delegator
        """
        logger.info(
            "Checking for potential adjustment for recently completed cycle {:s}.".format(
                str(completed_cycle)
            )
        )
        completed_cycle_report_file_path = get_calculation_report_file_path(
            self.calculations_dir, completed_cycle
        )
        adjustments = {}
        if os.path.isfile(completed_cycle_report_file_path):
            logger.info(
                "TRD ran for cycle: {:s}, calculating adjustments.".format(
                    str(completed_cycle)
                )
            )
            (
                reward_logs_from_report,
                total_amount_from_report,
                rewards_type_from_report,
                _,
            ) = CsvCalculationFileParser().parse(
                completed_cycle_report_file_path, self.baking_address
            )
            # check that the overestimate has not been computed yet
            if sum([rl.overestimate or 0 for rl in reward_logs_from_report]) > 0:
                logger.info(
                    "Overestimate has already been calculated for cycle {:s}, not calculating it again.".format(
                        str(completed_cycle)
                    )
                )
                completed_cycle_reward_logs, completed_cycle_total_amount = (
                    reward_logs_from_report,
                    total_amount_from_report,
                )
            else:
                (
                    completed_cycle_reward_logs,
                    completed_cycle_total_amount,
                ) = self.compute_rewards(
                    completed_cycle, computation_type, network_config
                )
            overestimate = int(total_amount_from_report - completed_cycle_total_amount)
            logger.info(
                "We {:s}estimated payout for cycle {:s} by {:<,d} mutez, will attempt to adjust.".format(
                    ("over" if overestimate > 0 else "under"),
                    str(completed_cycle),
                    abs(overestimate),
                )
            )
            for rl in reward_logs_from_report:
                # overwrite only overestimate in report csv file, leave the rest alone
                rl.overestimate = int(
                    Decimal(rl.ratio * overestimate).to_integral_value(
                        rounding=ROUND_HALF_DOWN
                    )
                )
                # we adjust the cycle we are paying out with the overestimate of the
                # just completed cycle
                adjustments[rl.address] = rl.overestimate
                logger.debug(
                    f"Will try to recover {adjustments[rl.address]} mutez for {rl.address} based on past overpayment"
                )

            CsvCalculationFileParser().write(
                reward_logs_from_report,
                completed_cycle_report_file_path,
                total_amount_from_report,
                rewards_type_from_report,
                self.baking_address,
                False,
            )
        return adjustments

    def try_to_pay(self, pymnt_cycle, rewards_type, network_config, current_cycle):
        try:
            logger.info("Payment cycle is {:s}".format(str(pymnt_cycle)))

            # 0- check for past payment evidence for current cycle
            past_payment_state = check_past_payment(self.payments_root, pymnt_cycle)

            if past_payment_state:
                logger.warn(past_payment_state)
                return True

            adjustments = {}
            early_payout = False
            current_cycle_rewards_type = rewards_type
            # 1- adjust past cycle if necessary
            if (
                self.release_override == -(network_config["PRESERVED_CYCLES"] + 1)
                and pymnt_cycle >= current_cycle
            ):
                early_payout = True
                completed_cycle = pymnt_cycle - network_config["PRESERVED_CYCLES"] - 1
                adjustments = self.recompute_rewards(
                    completed_cycle, rewards_type, network_config
                )
                # payout for current cycle will be estimated since we don't know actual rewards yet
                current_cycle_rewards_type = RewardsType.ESTIMATED

            # 2- get reward data and compute how to distribute them
            reward_logs, total_amount = self.compute_rewards(
                pymnt_cycle, current_cycle_rewards_type, network_config, adjustments
            )
            total_recovered_adjustments = int(
                sum([rl.adjustment for rl in reward_logs])
            )
            total_adjustments_to_recover = int(sum(adjustments.values()))
            if total_adjustments_to_recover > 0:
                logger.debug(
                    "Total adjustments to recover is {:<,d} mutez, total recovered adjustment is {:<,d} mutez.".format(
                        total_adjustments_to_recover, total_recovered_adjustments
                    )
                )
                logger.info(
                    "After early payout of cycle {:s}, {:<,d} mutez were not recovered.".format(
                        str(completed_cycle),
                        total_adjustments_to_recover + total_recovered_adjustments,
                    )
                )

            # 3- create calculations report file. This file contains calculations details
            report_file_path = get_calculation_report_file_path(
                self.calculations_dir, pymnt_cycle
            )
            logger.debug("Creating calculation report (%s)", report_file_path)
            CsvCalculationFileParser().write(
                reward_logs,
                report_file_path,
                total_amount,
                current_cycle_rewards_type,
                self.baking_address,
                early_payout,
            )

            # 4- set cycle info
            for reward_log in reward_logs:
                reward_log.cycle = pymnt_cycle
            total_amount_to_pay = int(
                sum(
                    [
                        reward_log.adjusted_amount
                        for reward_log in reward_logs
                        if reward_log.payable
                    ]
                )
            )

            # 5- if total_rewards > 0, proceed with payment
            if total_amount_to_pay > 0:
                self.payments_queue.put(PaymentBatch(self, pymnt_cycle, reward_logs))

                sleep(5.0)

                # 6- processing of cycle is done
                logger.info(
                    "Reward creation is done for cycle {}, created {} rewards.".format(
                        pymnt_cycle, len(reward_logs)
                    )
                )

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
            sleep(self.nw_config["MINIMAL_BLOCK_DELAY"])

            # if shutting down, exit
            if not self.life_cycle.is_running():
                self.exit(ExitCode.SUCCESS)
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
                logger.debug(
                    "Current time is '{}', latest block of local node is '{}'.".format(
                        utc_time, boot_time
                    )
                )
                return False
        except ValueError:
            logger.error(
                "Unable to determine local node's bootstrap status. Continuing..."
            )
        return True

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
        self.consumer_failure = True
        pass
