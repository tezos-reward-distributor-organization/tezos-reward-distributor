import json
import logging
import queue
import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM
from enum import Enum, auto
from time import sleep

from Constants import VERSION, RunMode
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
from log_config import main_logger, init
from plugins import plugins

logger = main_logger
LINER = "--------------------------------------------"
BUF_SIZE = 50


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
    NO_CONSUMERS_READY = auto()
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
    SHUT_DOWN = auto()


class ProcessLifeCycle:
    def __init__(self, args):
        self.lock_taken = False
        self.args = args
        self.node_client = None
        self.nw_config = None
        self.cfg = None
        self.baking_dirs = None
        self.srvc_fee_calc = None
        self.plugins_manager = None
        self.payments_queue = queue.Queue(BUF_SIZE)

        fsm_builder = TransitionsFsmBuilder()
        fsm_builder.add_initial_state(TrdState.INITIAL, on_leave=lambda e: logger.debug("TRD is starting..."))
        fsm_builder.add_state(TrdState.CMD_ARGS_PARSED, on_enter=self.do_parse_args)
        fsm_builder.add_state(TrdState.CMD_ARGS_GIVEN, on_enter=self.print_argument_configuration)
        fsm_builder.add_state(TrdState.BANNER_PRINTED, on_enter=self.do_print_banner)
        fsm_builder.add_state(TrdState.LOGGERS_INITIATED, on_enter=self.do_initiate_loggers)
        fsm_builder.add_state(TrdState.NODE_CLIENT_BUILT, on_enter=self.do_build_node_client)
        fsm_builder.add_state(TrdState.NW_CONFIG_BUILT, on_enter=self.do_build_nw_config)
        fsm_builder.add_state(TrdState.CONFIG_LOADED, on_enter=self.do_load_config)
        fsm_builder.add_state(TrdState.DIRS_SET_UP, on_enter=self.do_set_up_dirs)
        fsm_builder.add_state(TrdState.SIGNALS_REGISTERED, on_enter=self.do_register_signals)
        fsm_builder.add_state(TrdState.LOCKED, on_enter=self.do_lock)
        fsm_builder.add_state(TrdState.NOT_LOCKED, on_enter=lambda e: logger.debug("No locking needed!"))
        fsm_builder.add_state(TrdState.FEES_INIT, on_enter=self.do_init_service_fees)
        fsm_builder.add_state(TrdState.PLUGINS_LOADED, on_enter=self.do_load_plugins)
        fsm_builder.add_state(TrdState.PRODUCERS_READY, on_enter=self.do_launch_producers)
        fsm_builder.add_state(TrdState.CONSUMERS_READY, on_enter=self.do_launch_consumers)
        fsm_builder.add_state(TrdState.NO_CONSUMERS_READY, on_enter=lambda e: logger.debug("No consumers needed!"))
        fsm_builder.add_state(TrdState.READY, on_enter=self.print_ready)
        fsm_builder.add_final_state(TrdState.SHUTTING, on_enter=self.do_shut_down)

        fsm_builder.add_conditional_transition(TrdEvent.LAUNCH, TrdState.INITIAL, self.is_args_not_set, TrdState.CMD_ARGS_PARSED, TrdState.CMD_ARGS_GIVEN)
        fsm_builder.add_transition(TrdEvent.PRINT_BANNER, [TrdState.CMD_ARGS_PARSED, TrdState.CMD_ARGS_GIVEN], TrdState.BANNER_PRINTED)
        fsm_builder.add_transition(TrdEvent.INITIATE_LOGGERS, TrdState.BANNER_PRINTED, TrdState.LOGGERS_INITIATED)
        fsm_builder.add_transition(TrdEvent.BUILD_NODE_CLIENT, TrdState.LOGGERS_INITIATED, TrdState.NODE_CLIENT_BUILT)
        fsm_builder.add_transition(TrdEvent.BUILD_NW_CONFIG, TrdState.NODE_CLIENT_BUILT, TrdState.NW_CONFIG_BUILT)
        fsm_builder.add_transition(TrdEvent.LOAD_CONFIG, TrdState.NW_CONFIG_BUILT, TrdState.CONFIG_LOADED)
        fsm_builder.add_transition(TrdEvent.SET_UP_DIRS, TrdState.CONFIG_LOADED, TrdState.DIRS_SET_UP)
        fsm_builder.add_transition(TrdEvent.REGISTER_SIGNALS, TrdState.DIRS_SET_UP, TrdState.SIGNALS_REGISTERED)

        fsm_builder.add_conditional_transition(TrdEvent.LOCK, TrdState.SIGNALS_REGISTERED, self.is_dry_run, TrdState.NOT_LOCKED, TrdState.LOCKED)
        fsm_builder.add_transition(TrdEvent.INIT_FEES, [TrdState.LOCKED, TrdState.NOT_LOCKED], TrdState.FEES_INIT)
        fsm_builder.add_transition(TrdEvent.LOAD_PLUGINS, TrdState.FEES_INIT, TrdState.PLUGINS_LOADED)

        fsm_builder.add_transition(TrdEvent.LAUNCH_PRODUCERS, TrdState.PLUGINS_LOADED, TrdState.PRODUCERS_READY)
        fsm_builder.add_conditional_transition(TrdEvent.LAUNCH_CONSUMERS, TrdState.PRODUCERS_READY, self.is_dry_run_no_consumers, TrdState.NO_CONSUMERS_READY, TrdState.CONSUMERS_READY)
        fsm_builder.add_transition(TrdEvent.GO_READY, [TrdState.CONSUMERS_READY, TrdState.NO_CONSUMERS_READY], TrdState.READY)
        fsm_builder.add_global_transition(TrdEvent.SHUT_DOWN, TrdState.SHUTTING)

        self.fsm = fsm_builder.build()
        pass

    def print_baking_config(self):
        logger.info("Baking Configuration {}".format(self.cfg))

        logger.info(LINER)
        logger.info("BAKING ADDRESS is {}".format(self.cfg.get_baking_address()))
        logger.info("PAYMENT ADDRESS is {}".format(self.cfg.get_payment_address()))
        logger.info(LINER)

    @staticmethod
    def print_ready(e):
        logger.info("Application is READY!")
        logger.info(LINER)

    def start(self):
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

        # Run forever
        try:
            while self.is_running():
                sleep(10)
        except KeyboardInterrupt:
            logger.info("Interrupted.")
            self.shut_down()
        pass

    def do_parse_args(self, e):
        self.args = parse_arguments()

    def print_argument_configuration(self, e=None):
        mode = "daemon" if self.args.background_service else "interactive"
        logger.info("TRD version {} is running in {} mode.".format(VERSION, mode))

        if self.args.dry_run:
            logger.info(LINER)
            logger.info("DRY RUN MODE")
            logger.info(LINER)

        if logger.isEnabledFor(logging.INFO): logger.info(
            "Arguments Configuration = {}".format(json.dumps(self.args.__dict__, indent=1)))

        publish_stats = not self.args.do_not_publish_stats
        msg = "will" if publish_stats else "will not"
        logger.info("Anonymous statistics {} be collected. See docs/statistics.rst for more information.".format(msg))

    def do_print_banner(self, e):
        print_banner(self.args, script_name="")

    def do_initiate_loggers(self, e):
        init(self.args.syslog, self.args.log_file, self.args.verbose == 'on')
        self.print_argument_configuration()

    def do_build_node_client(self, e):
        self.node_client = ClientManager(self.args.node_endpoint, self.args.signer_endpoint)

    def do_build_nw_config(self, e):
        network_config_map = init_network_config(self.args.network, self.node_client)
        self.nw_config = network_config_map[self.args.network]

    def do_load_config(self, e):
        cfg_life_cycle = ConfigLifeCycle(self.args, self.nw_config, self.node_client, self.set_cfg)
        cfg_life_cycle.start()
        self.print_baking_config()

    def set_cfg(self, cfg):
        self.cfg = cfg

    def do_set_up_dirs(self, e):
        self.baking_dirs = BakingDirs(self.args, self.cfg.get_baking_address())

    def do_register_signals(self, e):
        for sig in (SIGABRT, SIGILL, SIGSEGV, SIGTERM):
            signal.signal(sig, self.stop_handler)

    def do_init_service_fees(self, e):
        self.srvc_fee_calc = ServiceFeeCalculator(self.cfg.get_full_supporters_set(), self.cfg.get_specials_map(), self.cfg.get_service_fee())

    def do_lock(self, e):
        LockFile().lock()
        self.lock_taken = True

    def do_load_plugins(self, e):
        self.plugins_manager = plugins.PluginManager(self.cfg.get_plugins_conf(), self.args.dry_run)

    def do_launch_producers(self, e):
        PaymentProducer(name='producer',
                        initial_payment_cycle=self.args.initial_cycle,
                        network_config=self.nw_config,
                        payments_dir=self.baking_dirs.payments_root,
                        calculations_dir=self.baking_dirs.calculations_root,
                        run_mode=RunMode(self.args.run_mode),
                        service_fee_calc=self.srvc_fee_calc,
                        release_override=self.args.release_override,
                        payment_offset=self.args.payment_offset,
                        baking_cfg=self.cfg,
                        life_cycle=self,
                        payments_queue=self.payments_queue,
                        dry_run=self.args.dry_run,
                        client_manager=self.node_client,
                        node_url=self.args.node_endpoint,
                        reward_data_provider=self.args.reward_data_provider,
                        node_url_public=self.args.node_addr_public,
                        api_base_url=self.args.api_base_url,
                        retry_injected=self.args.retry_injected).start()

    def do_launch_consumers(self, e):
        PaymentConsumer(name='consumer0',
                        payments_dir=self.baking_dirs.payments_root,
                        key_name=self.cfg.get_payment_address(),
                        payments_queue=self.payments_queue,
                        node_addr=self.args.node_endpoint,
                        client_manager=self.node_client,
                        plugins_manager=self.plugins_manager,
                        rewards_type=self.cfg.get_rewards_type(),
                        args=self.args,
                        dry_run=self.args.dry_run,
                        reactivate_zeroed=self.cfg.get_reactivate_zeroed(),
                        delegator_pays_ra_fee=self.cfg.get_delegator_pays_ra_fee(),
                        delegator_pays_xfer_fee=self.cfg.get_delegator_pays_xfer_fee(),
                        dest_map=self.cfg.get_dest_map(),
                        network_config=self.nw_config,
                        publish_stats=not self.args.do_not_publish_stats).start()

    def do_shut_down(self, e):
        logger.info("TRD is shutting down...")

        logger.info("--------------------------------------------------------")
        logger.info("Sensitive operations are in progress!")
        logger.info("Please wait while the application is being shut down!")
        logger.info("--------------------------------------------------------")

        if self.lock_taken:
            LockFile().release()
            logger.info("Lock file removed!")

    def stop_handler(self, signum, frame):
        logger.info("Application stop handler called: {}".format(signum))
        self.shut_down()

    def shut_down(self):
        self.fsm.trigger_event(TrdEvent.SHUT_DOWN)

    def is_running(self):
        return not self.fsm.is_complete()

    def is_dry_run(self, e):
        return self.args.dry_run

    def is_dry_run_no_consumers(self, e):
        return self.args.dry_run_no_consumers

    def is_args_not_set(self, e):
        return self.args is None
