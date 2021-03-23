import json
import logging
import signal
from _signal import SIGABRT, SIGILL, SIGSEGV, SIGTERM
from enum import Enum

from Constants import VERSION
from NetworkConfiguration import init_network_config
from cli.client_manager import ClientManager
from fsm.FsmBuilder import FsmBuilder
from launch_common import print_banner, parse_arguments
from util.config_life_cycle import ConfigLifeCycle
from util.lock_file import LockFile
from log_config import main_logger, init

logger = main_logger


class TrdState(Enum):
    INITIAL = 0
    CMD_ARGS_PARSED = 1
    BANNER_PRINTED = 2
    LOGGERS_INITIATED = 3
    NODE_CLIENT_BUILT = 4
    NW_CONFIG_BUILT = 5
    CONFIG_LOADED = 6


class TrdEvent(Enum):
    LAUNCH = 1
    PRINT_BANNER = 2
    INITIATE_LOGGERS = 3
    BUILD_NODE_CLIENT = 4
    BUILD_NW_CONFIG = 5
    LOAD_CONFIG = 6


class ProcessLifeCycle:
    def __init__(self):
        self.lock_file = LockFile()
        self.running = False
        self.lock_taken = False
        self.args = None
        self.node_client = None
        self.nw_config = None
        self.cfg = None

        fsm_builder = FsmBuilder()
        fsm_builder.add_initial_state(TrdState.INITIAL, on_leave=lambda e: logger.debug("TRD is starting..."))
        fsm_builder.add_state(TrdState.CMD_ARGS_PARSED, on_enter=self.print_argument_configuration)
        fsm_builder.add_state(TrdState.BANNER_PRINTED)
        fsm_builder.add_state(TrdState.LOGGERS_INITIATED)
        fsm_builder.add_state(TrdState.NODE_CLIENT_BUILT)
        fsm_builder.add_state(TrdState.NW_CONFIG_BUILT)
        fsm_builder.add_state(TrdState.CONFIG_LOADED)

        fsm_builder.add_transition(TrdEvent.LAUNCH, TrdState.INITIAL, TrdState.CMD_ARGS_PARSED, on_before=self.do_parse_args)
        fsm_builder.add_transition(TrdEvent.PRINT_BANNER, TrdState.CMD_ARGS_PARSED, TrdState.BANNER_PRINTED, on_before=self.do_print_banner)
        fsm_builder.add_transition(TrdEvent.INITIATE_LOGGERS, TrdState.BANNER_PRINTED, TrdState.LOGGERS_INITIATED, on_before=self.do_initiate_loggers)
        fsm_builder.add_transition(TrdEvent.BUILD_NODE_CLIENT, TrdState.LOGGERS_INITIATED, TrdState.NODE_CLIENT_BUILT, on_before=self.do_build_node_client())
        fsm_builder.add_transition(TrdEvent.BUILD_NW_CONFIG, TrdState.NODE_CLIENT_BUILT, TrdState.NW_CONFIG_BUILT, on_before=self.do_build_nw_config)
        fsm_builder.add_transition(TrdEvent.LOAD_CONFIG, TrdState.NW_CONFIG_BUILT, TrdState.CONFIG_LOADED, on_before=self.do_load_config)

        self.fsm = fsm_builder.build()
        pass

    def start(self):
        self.fsm.trigger(TrdEvent.LAUNCH)
        self.fsm.trigger(TrdEvent.PRINT_BANNER)
        self.fsm.trigger(TrdEvent.INITIATE_LOGGERS)
        self.fsm.trigger(TrdEvent.BUILD_NODE_CLIENT)
        self.fsm.trigger(TrdEvent.BUILD_NW_CONFIG)

    def do_load_config(self):
        cfg_life_cycle = ConfigLifeCycle(self.args, self.nw_config, self.node_client, self.set_cfg)
        cfg_life_cycle.start()

    def set_cfg(self, cfg):
        self.cfg = cfg

    def print_argument_configuration(self):
        mode = "daemon" if self.args.background_service else "interactive"
        logger.info("TRD version {} is running in {} mode.".format(VERSION, mode))

        if logger.isEnabledFor(logging.INFO): logger.info("Arguments Configuration = {}".format(json.dumps(self.args.__dict__, indent=1)))

        publish_stats = not self.args.do_not_publish_stats
        msg = "will" if publish_stats else "will not"
        logger.info("Anonymous statistics {} be collected. See docs/statistics.rst for more information.".format(msg))

    def do_parse_args(self):
        self.args = parse_arguments()

    def do_print_banner(self):
        print_banner(self.args, script_name="")

    def do_initiate_loggers(self):
        init(self.args.syslog, self.args.log_file, self.args.verbose == 'on')

    def do_build_node_client(self):
        self.node_client = ClientManager(self.args.node_endpoint, self.args.signer_endpoint)

    def do_build_nw_config(self):
        network_config_map = init_network_config(self.args.network, self.node_client)
        self.nw_config = network_config_map[self.args.network]

    def do_register_signals(self):
        for sig in (SIGABRT, SIGILL, SIGSEGV, SIGTERM):
            signal.signal(sig, self.stop_handler)

    def do_lock(self):
        self.lock_file.lock()
        self.lock_taken = True

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
