import json
import logging
import queue
import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM
from enum import Enum, auto

from Constants import VERSION, RunMode
from NetworkConfiguration import init_network_config
from calc.service_fee_calculator import ServiceFeeCalculator
from cli.client_manager import ClientManager
from fsm.FsmBuilder import FsmBuilder
from launch_common import print_banner, parse_arguments
from model.baking_dirs import BakingDirs
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
    BANNER_PRINTED = auto()
    LOGGERS_INITIATED = auto()
    NODE_CLIENT_BUILT = auto()
    NW_CONFIG_BUILT = auto()
    CONFIG_LOADED = auto()
    DIRS_SET_UP = auto()
    SIGNALS_REGISTERED = auto()
    LOCKED = auto()
    FEES_INIT = auto()
    PLUGINS_LOADED = auto()
    PRODUCERS_READY = auto()
    CONSUMERS_READY = auto()


class TrdEvent(Enum):
    LAUNCH = auto()
    PRINT_BANNER = auto()
    INITIATE_LOGGERS = auto()
    BUILD_NODE_CLIENT = auto()
    BUILD_NW_CONFIG = auto()
    LOAD_CONFIG = auto()
    SET_UP_DIRS = auto()
    REGISTER_SIGNALS = auto()
    CHECK_DRY_RUN = auto()
    INIT_FEES = auto()
    LOAD_PLUGINS = auto()
    LAUNCH_PRODUCERS = auto()
    LAUNCH_CONSUMERS = auto()


class ProcessLifeCycle:
    def __init__(self):
        self.lock_file = LockFile()
        self.running = False
        self.lock_taken = False
        self.args = None
        self.node_client = None
        self.nw_config = None
        self.cfg = None
        self.baking_dirs = None
        self.srvc_fee_calc = None
        self.plugins_manager = None
        self.payments_queue = queue.Queue(BUF_SIZE)

        fsm_builder = FsmBuilder()
        fsm_builder.add_initial_state(TrdState.INITIAL, on_leave=lambda e: logger.debug("TRD is starting..."))
        fsm_builder.add_state(TrdState.CMD_ARGS_PARSED, on_enter=self.print_argument_configuration)
        fsm_builder.add_state(TrdState.BANNER_PRINTED)
        fsm_builder.add_state(TrdState.LOGGERS_INITIATED)
        fsm_builder.add_state(TrdState.NODE_CLIENT_BUILT)
        fsm_builder.add_state(TrdState.NW_CONFIG_BUILT)
        fsm_builder.add_state(TrdState.CONFIG_LOADED, on_enter=self.do_print_baking_config)
        fsm_builder.add_state(TrdState.DIRS_SET_UP)
        fsm_builder.add_state(TrdState.SIGNALS_REGISTERED)
        fsm_builder.add_state(TrdState.LOCKED)
        fsm_builder.add_state(TrdState.FEES_INIT)
        fsm_builder.add_state(TrdState.PLUGINS_LOADED)
        fsm_builder.add_state(TrdState.PRODUCERS_READY)
        fsm_builder.add_state(TrdState.CONSUMERS_READY)

        fsm_builder.add_transition(TrdEvent.LAUNCH, TrdState.INITIAL, TrdState.CMD_ARGS_PARSED, on_before=self.do_parse_args)
        fsm_builder.add_transition(TrdEvent.PRINT_BANNER, TrdState.CMD_ARGS_PARSED, TrdState.BANNER_PRINTED, on_before=self.do_print_banner)
        fsm_builder.add_transition(TrdEvent.INITIATE_LOGGERS, TrdState.BANNER_PRINTED, TrdState.LOGGERS_INITIATED, on_before=self.do_initiate_loggers)
        fsm_builder.add_transition(TrdEvent.BUILD_NODE_CLIENT, TrdState.LOGGERS_INITIATED, TrdState.NODE_CLIENT_BUILT, on_before=self.do_build_node_client)
        fsm_builder.add_transition(TrdEvent.BUILD_NW_CONFIG, TrdState.NODE_CLIENT_BUILT, TrdState.NW_CONFIG_BUILT, on_before=self.do_build_nw_config)
        fsm_builder.add_transition(TrdEvent.LOAD_CONFIG, TrdState.NW_CONFIG_BUILT, TrdState.CONFIG_LOADED, on_before=self.do_load_config)
        fsm_builder.add_transition(TrdEvent.SET_UP_DIRS, TrdState.CONFIG_LOADED, TrdState.DIRS_SET_UP, on_before=self.do_set_up_dirs)
        fsm_builder.add_transition(TrdEvent.REGISTER_SIGNALS, TrdState.DIRS_SET_UP, TrdState.SIGNALS_REGISTERED, on_before=self.do_register_signals)

        fsm_builder.add_transition(TrdEvent.CHECK_DRY_RUN, TrdState.SIGNALS_REGISTERED, TrdState.LOCKED, on_before=self.do_lock, conditions=[lambda e: not self.args.dry_drun])
        fsm_builder.add_transition(TrdEvent.CHECK_DRY_RUN, TrdState.SIGNALS_REGISTERED, TrdState.FEES_INIT, on_before=self.do_init_service_fees, conditions=[lambda e: self.args.dry_drun])
        fsm_builder.add_transition(TrdEvent.INIT_FEES, TrdState.LOCKED, TrdState.FEES_INIT, on_before=self.do_init_service_fees)
        fsm_builder.add_transition(TrdEvent.LOAD_PLUGINS, TrdState.FEES_INIT, TrdState.PLUGINS_LOADED, on_before=self.do_load_plugins)

        fsm_builder.add_transition(TrdEvent.LAUNCH_PRODUCERS, TrdState.PLUGINS_LOADED, TrdState.PRODUCERS_READY, on_before=self.do_launch_producers)
        fsm_builder.add_transition(TrdEvent.LAUNCH_CONSUMERS, TrdState.PRODUCERS_READY, TrdState.CONSUMERS_READY, on_before=self.do_launch_consumers)

        self.fsm = fsm_builder.build()
        pass

    def print_argument_configuration(self, e):
        mode = "daemon" if self.args.background_service else "interactive"
        logger.info("TRD version {} is running in {} mode.".format(VERSION, mode))

        if logger.isEnabledFor(logging.INFO): logger.info("Arguments Configuration = {}".format(json.dumps(self.args.__dict__, indent=1)))

        publish_stats = not self.args.do_not_publish_stats
        msg = "will" if publish_stats else "will not"
        logger.info("Anonymous statistics {} be collected. See docs/statistics.rst for more information.".format(msg))

    def do_print_baking_config(self, e):
        logger.info("Baking Configuration {}".format(self.cfg))

        logger.info(LINER)
        logger.info("BAKING ADDRESS is {}".format(self.cfg.get_baking_address()))
        logger.info("PAYMENT ADDRESS is {}".format(self.cfg.get_payment_address()))
        logger.info(LINER)

    def start(self):
        self.fsm.trigger(TrdEvent.LAUNCH)
        self.fsm.trigger(TrdEvent.PRINT_BANNER)
        self.fsm.trigger(TrdEvent.INITIATE_LOGGERS)
        self.fsm.trigger(TrdEvent.BUILD_NODE_CLIENT)
        self.fsm.trigger(TrdEvent.BUILD_NW_CONFIG)
        self.fsm.trigger(TrdEvent.LOAD_CONFIG)
        self.fsm.trigger(TrdEvent.SET_UP_DIRS)
        self.fsm.trigger(TrdEvent.REGISTER_SIGNALS)
        self.fsm.trigger(TrdEvent.CHECK_DRY_RUN)
        self.fsm.trigger_if_not_in_state(TrdEvent.INIT_FEES, TrdState.FEES_INIT)
        self.fsm.trigger(TrdEvent.LOAD_PLUGINS)

        self.fsm.trigger(TrdEvent.LAUNCH_PRODUCERS)
        self.fsm.trigger(TrdEvent.LAUNCH_CONSUMERS)

        pass

    def do_parse_args(self, e):
        self.args = parse_arguments()

    def do_print_banner(self, e):
        print_banner(self.args, script_name="")

    def do_initiate_loggers(self, e):
        init(self.args.syslog, self.args.log_file, self.args.verbose == 'on')

    def do_build_node_client(self, e):
        self.node_client = ClientManager(self.args.node_endpoint, self.args.signer_endpoint)

    def do_build_nw_config(self, e):
        network_config_map = init_network_config(self.args.network, self.node_client)
        self.nw_config = network_config_map[self.args.network]

    def do_load_config(self, e):
        cfg_life_cycle = ConfigLifeCycle(self.args, self.nw_config, self.node_client, self.set_cfg)
        cfg_life_cycle.start()

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
        self.lock_file.lock()
        self.lock_taken = True

    def do_load_plugins(self, e):
        self.plugins_manager = plugins.PluginManager(self.cfg.get_plugins_conf(), self.args.dry_run)

    def do_launch_producers(self, e):
        pass

    def do_launch_consumers(self, e):
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

    def stop(self):
        logger.info("--------------------------------------------------------")
        logger.info("Sensitive operations are in progress!")
        logger.info("Please wait while the application is being shut down!")
        logger.info("--------------------------------------------------------")
        if self.lock_taken:
            self.lock_file.release()
            logger.info("Lock file removed!")
        self.running = False

    def stop_handler(self, signum):
        logger.info("Application stop handler called: {}".format(signum))
        self.stop()

    def is_running(self):
        return not self.fsm.is_finished()
