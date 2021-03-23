from enum import Enum

from api.provider_factory import ProviderFactory
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from fsm.FsmBuilder import FsmBuilder
from log_config import main_logger
import os

from model.baking_conf import BakingConf

logger = main_logger


class ConfigState(Enum):
    INITIAL = 0
    READ = 1
    BUILT = 2
    PARSED = 3
    VALIDATED = 4
    PROCESSED = 5


class ConfigEvent(Enum):
    READ = 1
    BUILD = 2
    PARSE = 3
    VALIDATE = 4
    PROCESS = 5


class ConfigLifeCycle:

    def __init__(self, args, nw_cfg, node_client, callback):
        self.args = args
        self.nw_cfg = nw_cfg
        self.node_client = node_client

        self.config_text = None
        self.parser = None

        fsm_builder = FsmBuilder()
        fsm_builder.add_initial_state(ConfigState.INITIAL, on_leave=lambda e: logger.debug("Loading baking configuration file ..."))
        fsm_builder.add_state(ConfigState.BUILT)
        fsm_builder.add_state(ConfigState.READ)
        fsm_builder.add_state(ConfigState.PARSED)
        fsm_builder.add_state(ConfigState.VALIDATED)
        fsm_builder.add_final_state(ConfigState.PROCESSED, on_enter=lambda e: callback(conf=self.get_conf()))

        fsm_builder.add_transition(ConfigEvent.READ, ConfigState.INITIAL, ConfigState.READ, on_before=self.do_read_cfg_file)
        fsm_builder.add_transition(ConfigEvent.BUILD, ConfigState.READ, ConfigState.BUILT, on_before=self.do_build_parser)
        fsm_builder.add_transition(ConfigEvent.PARSE, ConfigState.BUILT, ConfigState.PARSED, on_before=self.do_parse_cfg)
        fsm_builder.add_transition(ConfigEvent.VALIDATE, ConfigState.PARSED, ConfigState.VALIDATED, on_before=self.do_validate_cfg)
        fsm_builder.add_transition(ConfigEvent.PROCESS, ConfigState.VALIDATED, ConfigState.PROCESSED, on_before=self.do_process_cfg)

        self.fsm = fsm_builder.build()

        pass

    def start(self):
        self.fsm.trigger(ConfigEvent.READ)
        self.fsm.trigger(ConfigEvent.BUILD)
        self.fsm.trigger(ConfigEvent.PARSE)
        self.fsm.trigger(ConfigEvent.VALIDATE)
        self.fsm.trigger(ConfigEvent.PROCESS)

    def do_read_cfg_file(self):
        config_dir = os.path.expanduser(self.args.config_dir)

        # create configuration directory if it is not present
        # so that user can easily put his configuration there
        if config_dir and not os.path.exists(config_dir):
            logger.debug("Creating path '{}'".format(config_dir))
            os.makedirs(config_dir)

        config_file_path = self.get_baking_cfg_file(config_dir)

        logger.info("Loading baking configuration file {}".format(config_file_path))

        self.config_text = ConfigParser.load_file(config_file_path)

    def do_build_parser(self):
        provider_factory = ProviderFactory(self.args.reward_data_provider)

        self.parser = BakingYamlConfParser(yaml_text=self.config_text, clnt_mngr=self.node_client,
                                           provider_factory=provider_factory, network_config=self.nw_cfg,
                                           node_url=self.args.node_endpoint, api_base_url=self.args.api_base_url)
        pass

    def do_parse_cfg(self):
        self.parser.parse()

    def do_validate_cfg(self):
        self.parser.validate()

    def do_process_cfg(self):
        self.parser.process()

    def get_conf(self):
        cfg_dict = self.parser.get_conf_obj()
        return BakingConf(cfg_dict)

    @staticmethod
    def get_baking_cfg_file(cfg_dir):
        cfg_file = None
        for file in os.listdir(cfg_dir):
            if file.endswith(".yaml") and not file.startswith("master"):
                if cfg_file:
                    raise Exception("Application only supports one baking configuration file. Found at least 2 {}, {}".format(cfg_file, file))
                cfg_file = file

        if cfg_file is None:
            raise Exception("Unable to find any '.yaml' configuration files inside configuration directory({})".format(cfg_dir))

        return os.path.join(cfg_dir, cfg_file)