import json
import logging
import queue
import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM
from enum import Enum, auto
from time import sleep

from Constants import VERSION, RunMode, LINER, BUF_SIZE
from NetworkConfiguration import init_network_config
from calc.service_fee_calculator import ServiceFeeCalculator
from cli.client_manager import ClientManager
from fsm.TransitionsFsmBuilder import TransitionsFsmBuilder
from launch_common import print_banner, parse_arguments
from model.baking_dirs import BakingDirs
from pay.payment_consumer import PaymentConsumer
from pay.payment_producer import PaymentProducer
from util.config_life_cycle import ConfigLifeCycle
from util.lock_file import LockFile
from log_config import main_logger, init, verbose_logger
from plugins import plugins
from util.exit_program import exit_program, ExitCode

logger = main_logger


class TrdState(Enum):
    INITIAL = auto()
    CMD_ARGS_PARSED = auto()
    CMD_ARGS_GIVEN = auto()
    BANNER_PRINTED = auto()
    LOGGERS_INITIATED = auto()
    NODE_CLIENT_BUILT = auto()
    NW_CONFIG_BUILT = auto()
    CONFIG_LOADED = auto()
    DIRS_SET_UP = auto()
    SIGNALS_REGISTERED = auto()
    LOCKED = auto()
    NOT_LOCKED = auto()
    FEES_INIT = auto()
    PLUGINS_LOADED = auto()
    PRODUCERS_READY = auto()
    CONSUMERS_READY = auto()
    READY = auto()
    SHUTTING = auto()


class TrdEvent(Enum):
    LAUNCH = auto()
    PRINT_BANNER = auto()
    INITIATE_LOGGERS = auto()
    BUILD_NODE_CLIENT = auto()
    BUILD_NW_CONFIG = auto()
    LOAD_CONFIG = auto()
    SET_UP_DIRS = auto()
    REGISTER_SIGNALS = auto()
    LOCK = auto()
    INIT_FEES = auto()
    LOAD_PLUGINS = auto()
    LAUNCH_PRODUCERS = auto()
    LAUNCH_CONSUMERS = auto()
    GO_READY = auto()
    SHUT_DOWN_ON_ERROR = auto()
    SHUT_DOWN_ON_DEMAND = auto()


class ProcessLifeCycle:
    def __init__(self, args):
        self.__lock_taken = False
        self.__args = args
        self.__node_client = None
        self.__nw_config = None
        self.__cfg = None
        self.__baking_dirs = None
        self.__srvc_fee_calc = None
        self.__plugins_manager = None
        self.__payments_queue = queue.Queue(BUF_SIZE)

        self.fsm = self.get_fsm_builder().build()

    def get_fsm_builder(self):
        fsm_builder = TransitionsFsmBuilder()
        fsm_builder.add_initial_state(
            TrdState.INITIAL, on_leave=lambda e: logger.debug("TRD is starting...")
        )
        fsm_builder.add_state(TrdState.CMD_ARGS_PARSED, on_enter=self.do_parse_args)
        fsm_builder.add_state(
            TrdState.CMD_ARGS_GIVEN, on_enter=self.print_argument_configuration
        )
        fsm_builder.add_state(TrdState.BANNER_PRINTED, on_enter=self.do_print_banner)
        fsm_builder.add_state(
            TrdState.LOGGERS_INITIATED, on_enter=self.do_initiate_loggers
        )
        fsm_builder.add_state(
            TrdState.NODE_CLIENT_BUILT, on_enter=self.do_build_node_client
        )
        fsm_builder.add_state(
            TrdState.NW_CONFIG_BUILT, on_enter=self.do_build_nw_config
        )
        fsm_builder.add_state(TrdState.CONFIG_LOADED, on_enter=self.do_load_config)
        fsm_builder.add_state(TrdState.DIRS_SET_UP, on_enter=self.do_set_up_dirs)
        fsm_builder.add_state(
            TrdState.SIGNALS_REGISTERED, on_enter=self.do_register_signals
        )
        fsm_builder.add_state(TrdState.LOCKED, on_enter=self.do_lock)
        fsm_builder.add_state(
            TrdState.NOT_LOCKED, on_enter=lambda e: logger.debug("No locking needed!")
        )
        fsm_builder.add_state(TrdState.FEES_INIT, on_enter=self.do_init_service_fees)
        fsm_builder.add_state(TrdState.PLUGINS_LOADED, on_enter=self.do_load_plugins)
        fsm_builder.add_state(
            TrdState.PRODUCERS_READY, on_enter=self.do_launch_producers
        )
        fsm_builder.add_state(
            TrdState.CONSUMERS_READY, on_enter=self.do_launch_consumers
        )
        fsm_builder.add_state(TrdState.READY, on_enter=self.print_ready)
        fsm_builder.add_final_state(TrdState.SHUTTING, on_enter=self.do_shut_down)

        fsm_builder.add_conditional_transition(
            TrdEvent.LAUNCH,
            TrdState.INITIAL,
            self.is_args_not_set,
            TrdState.CMD_ARGS_PARSED,
            TrdState.CMD_ARGS_GIVEN,
        )
        fsm_builder.add_transition(
            TrdEvent.PRINT_BANNER,
            [TrdState.CMD_ARGS_PARSED, TrdState.CMD_ARGS_GIVEN],
            TrdState.BANNER_PRINTED,
        )
        fsm_builder.add_transition(
            TrdEvent.INITIATE_LOGGERS,
            TrdState.BANNER_PRINTED,
            TrdState.LOGGERS_INITIATED,
        )
        fsm_builder.add_transition(
            TrdEvent.BUILD_NODE_CLIENT,
            TrdState.LOGGERS_INITIATED,
            TrdState.NODE_CLIENT_BUILT,
        )
        fsm_builder.add_transition(
            TrdEvent.BUILD_NW_CONFIG,
            TrdState.NODE_CLIENT_BUILT,
            TrdState.NW_CONFIG_BUILT,
        )
        fsm_builder.add_transition(
            TrdEvent.LOAD_CONFIG, TrdState.NW_CONFIG_BUILT, TrdState.CONFIG_LOADED
        )
        fsm_builder.add_transition(
            TrdEvent.SET_UP_DIRS, TrdState.CONFIG_LOADED, TrdState.DIRS_SET_UP
        )
        fsm_builder.add_transition(
            TrdEvent.REGISTER_SIGNALS, TrdState.DIRS_SET_UP, TrdState.SIGNALS_REGISTERED
        )

        fsm_builder.add_conditional_transition(
            TrdEvent.LOCK,
            TrdState.SIGNALS_REGISTERED,
            self.is_dry_run,
            TrdState.NOT_LOCKED,
            TrdState.LOCKED,
        )
        fsm_builder.add_transition(
            TrdEvent.INIT_FEES,
            [TrdState.LOCKED, TrdState.NOT_LOCKED],
            TrdState.FEES_INIT,
        )
        fsm_builder.add_transition(
            TrdEvent.LOAD_PLUGINS, TrdState.FEES_INIT, TrdState.PLUGINS_LOADED
        )

        fsm_builder.add_transition(
            TrdEvent.LAUNCH_PRODUCERS, TrdState.PLUGINS_LOADED, TrdState.PRODUCERS_READY
        )
        fsm_builder.add_transition(
            TrdEvent.LAUNCH_CONSUMERS,
            TrdState.PRODUCERS_READY,
            TrdState.CONSUMERS_READY,
        )
        fsm_builder.add_transition(
            TrdEvent.GO_READY,
            TrdState.CONSUMERS_READY,
            TrdState.READY,
        )
        fsm_builder.add_transition(
            TrdEvent.SHUT_DOWN_ON_DEMAND, TrdState.READY, TrdState.SHUTTING
        )
        fsm_builder.add_global_transition(
            TrdEvent.SHUT_DOWN_ON_ERROR, TrdState.SHUTTING
        )

        return fsm_builder

    def print_baking_config(self):
        logger.info("Baking Configuration {}".format(self.__cfg))

        logger.info(LINER)
        logger.info("BAKING ADDRESS is {}".format(self.__cfg.get_baking_address()))
        logger.info("PAYMENT ADDRESS is {}".format(self.__cfg.get_payment_address()))
        logger.info(LINER)

    @staticmethod
    def print_ready(e):
        logger.info("Application is READY!")
        logger.info(LINER)

    def start(self):
        try:
            self.fsm.trigger_event(TrdEvent.LAUNCH)
            self.fsm.trigger_event(TrdEvent.PRINT_BANNER)
            self.fsm.trigger_event(TrdEvent.INITIATE_LOGGERS)
            self.fsm.trigger_event(TrdEvent.BUILD_NODE_CLIENT)
            self.fsm.trigger_event(TrdEvent.BUILD_NW_CONFIG)
            self.fsm.trigger_event(TrdEvent.LOAD_CONFIG)
            self.fsm.trigger_event(TrdEvent.SET_UP_DIRS)
            self.fsm.trigger_event(TrdEvent.REGISTER_SIGNALS)
            self.fsm.trigger_event(TrdEvent.LOCK)
            self.fsm.trigger_event(TrdEvent.INIT_FEES)
            self.fsm.trigger_event(TrdEvent.LOAD_PLUGINS)
            self.fsm.trigger_event(TrdEvent.LAUNCH_PRODUCERS)
            self.fsm.trigger_event(TrdEvent.LAUNCH_CONSUMERS)
            self.fsm.trigger_event(TrdEvent.GO_READY)

            while self.is_running:
                sleep(10)

        except KeyboardInterrupt:
            logger.info("Interrupted.")
            self.shut_down_on_error()
        except Exception as e:
            logger.error(
                "[Process Life Cycle completing With Failure] Error Details: {:s}".format(
                    str(e)
                )
            )
            verbose_logger.error(
                "[Process Life Cycle completing With Failure] Stack Trace: {}".format(
                    e
                ),
                stack_info=True,
            )

            self.shut_down_on_error()

    def do_parse_args(self, e):
        self.__args = parse_arguments()

    def print_argument_configuration(self, e=None):
        mode = "daemon" if self.args.background_service else "interactive"
        logger.info("TRD version {} is running in {} mode.".format(VERSION, mode))

        if self.args.dry_run:
            logger.info(LINER)
            logger.info("DRY RUN MODE")
            logger.info(LINER)

        if logger.isEnabledFor(logging.INFO):
            logger.info(
                "Arguments Configuration = {}".format(
                    json.dumps(self.args.__dict__, indent=1)
                )
            )

        publish_stats = not self.args.do_not_publish_stats
        msg = "will" if publish_stats else "will not"
        logger.info(
            "Anonymous statistics {} be collected. See docs/statistics.rst for more information.".format(
                msg
            )
        )

    def do_print_banner(self, e):
        print_banner(self.args, script_name="")

    def do_initiate_loggers(self, e):
        init(self.args.syslog, self.args.log_file, self.args.verbose == "on")
        self.print_argument_configuration()

    def do_build_node_client(self, e):
        self.__node_client = ClientManager(
            self.args.node_endpoint, self.args.signer_endpoint
        )

    def do_build_nw_config(self, e):
        network_config_map = init_network_config(self.args.network, self.__node_client)
        self.__nw_config = network_config_map[self.args.network]

    def do_load_config(self, e):
        cfg_life_cycle = ConfigLifeCycle(
            self.args, self.__nw_config, self.__node_client, self.set_cfg
        )
        cfg_life_cycle.start()
        self.print_baking_config()

    def set_cfg(self, cfg):
        self.__cfg = cfg

    def do_set_up_dirs(self, e):
        self.__baking_dirs = BakingDirs(self.args, self.__cfg.get_baking_address())

    def do_register_signals(self, e):
        for sig in (SIGABRT, SIGILL, SIGSEGV, SIGTERM):
            signal.signal(sig, self.stop_handler)

    def do_init_service_fees(self, e):
        self.__srvc_fee_calc = ServiceFeeCalculator(
            self.__cfg.get_full_supporters_set(),
            self.__cfg.get_specials_map(),
            self.__cfg.get_service_fee(),
        )

    def do_lock(self, e):
        LockFile(self.args).lock()
        self.__lock_taken = True

    def do_load_plugins(self, e):
        self.__plugins_manager = plugins.PluginManager(
            self.__cfg.get_plugins_conf(), self.args.dry_run
        )

    def do_launch_producers(self, e):
        PaymentProducer(
            name="producer",
            network_config=self.__nw_config,
            payments_dir=self.__baking_dirs.payments_root,
            calculations_dir=self.__baking_dirs.calculations_root,
            run_mode=RunMode(self.args.run_mode),
            service_fee_calc=self.__srvc_fee_calc,
            release_override=self.args.release_override,
            payment_offset=self.args.payment_offset,
            baking_cfg=self.__cfg,
            life_cycle=self,
            payments_queue=self.__payments_queue,
            dry_run=self.args.dry_run,
            client_manager=self.__node_client,
            node_url=self.args.node_endpoint,
            reward_data_provider=self.args.reward_data_provider,
            node_url_public=self.args.node_addr_public,
            api_base_url=self.args.api_base_url,
            retry_injected=self.args.retry_injected,
            initial_payment_cycle=self.args.initial_cycle,
        ).start()

    def do_launch_consumers(self, e):
        PaymentConsumer(
            name="consumer0",
            payments_dir=self.__baking_dirs.payments_root,
            key_name=self.__cfg.get_payment_address(),
            payments_queue=self.__payments_queue,
            node_addr=self.args.node_endpoint,
            client_manager=self.__node_client,
            plugins_manager=self.__plugins_manager,
            rewards_type=self.__cfg.get_rewards_type(),
            args=self.args,
            dry_run=self.args.dry_run,
            reactivate_zeroed=self.__cfg.get_reactivate_zeroed(),
            delegator_pays_ra_fee=self.__cfg.get_delegator_pays_ra_fee(),
            delegator_pays_xfer_fee=self.__cfg.get_delegator_pays_xfer_fee(),
            dest_map=self.__cfg.get_dest_map(),
            network_config=self.__nw_config,
            publish_stats=not self.args.do_not_publish_stats,
            calculations_dir=self.__baking_dirs.calculations_root,
            baking_address=self.__cfg.get_baking_address(),
        ).start()

    def do_shut_down(self, e):
        logger.info("TRD is shutting down...")

        logger.info("--------------------------------------------------------")
        logger.info("Sensitive operations are in progress!")
        logger.info("Please wait while the application is being shut down!")
        logger.info("--------------------------------------------------------")

        if self.__lock_taken:
            LockFile(self.args).release()
            logger.info("Lock file removed!")

    def stop_handler(self, signum, frame):
        logger.info("Application stop handler called: {}".format(signum))
        self.shut_down_on_error()

    def shut_down_on_error(self):
        self.fsm.trigger_event(TrdEvent.SHUT_DOWN_ON_ERROR)
        exit_program(ExitCode.GENERAL_ERROR, "Shutdown due to error!")

    def shut_down_on_demand(self):
        self.fsm.trigger_event(TrdEvent.SHUT_DOWN_ON_DEMAND)

    def is_running(self):
        return not self.fsm.is_complete

    @property
    def args(self):
        return self.__args

    def is_dry_run(self, e):
        return bool(self.args.dry_run)

    def is_args_not_set(self, e):
        return self.args is None
