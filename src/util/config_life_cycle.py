import os
from enum import Enum

from api.provider_factory import ProviderFactory
from config.config_parser import ConfigParser
from config.yaml_baking_conf_parser import BakingYamlConfParser
from fsm.TransitionsFsmBuilder import TransitionsFsmBuilder
from log_config import main_logger
from model.baking_conf import BakingConf
from Constants import CONFIG_DIR

logger = main_logger


class ConfigState(Enum):
    INITIAL = 0
    READ = 1
    BUILT = 2
    PARSED = 3
    VALIDATED = 4
    PROCESSED = 5
    COMPLETED = 6


class ConfigEvent(Enum):
    READ = 1
    BUILD = 2
    PARSE = 3
    VALIDATE = 4
    PROCESS = 5
    COMPLETE = 6


class ConfigLifeCycle:
    def __init__(self, args, nw_cfg, node_client, callback):
        self.__args = args
        self.__nw_cfg = nw_cfg
        self.__node_client = node_client

        self.__config_text = None
        self.__parser = None
        self.__callback = callback
        self.fsm = self.get_fsm_builder().build()

    def get_fsm_builder(self):
        fsm_builder = TransitionsFsmBuilder()
        fsm_builder.add_initial_state(
            ConfigState.INITIAL,
            on_leave=lambda e: logger.debug("Loading baking configuration file ..."),
        )
        fsm_builder.add_state(
            ConfigState.READ, on_enter=self.do_read_configuration_file
        )
        fsm_builder.add_state(ConfigState.BUILT, on_enter=self.do_build_parser)
        fsm_builder.add_state(ConfigState.PARSED, on_enter=self.do_parse_cfg)
        fsm_builder.add_state(ConfigState.VALIDATED, on_enter=self.do_validate_cfg)
        fsm_builder.add_state(ConfigState.PROCESSED, on_enter=self.do_process_cfg)
        fsm_builder.add_final_state(
            ConfigState.COMPLETED, on_enter=lambda e: self.__callback(self.get_conf())
        )

        fsm_builder.add_transition(
            ConfigEvent.READ, ConfigState.INITIAL, ConfigState.READ
        )
        fsm_builder.add_transition(
            ConfigEvent.BUILD, ConfigState.READ, ConfigState.BUILT
        )
        fsm_builder.add_transition(
            ConfigEvent.PARSE, ConfigState.BUILT, ConfigState.PARSED
        )
        fsm_builder.add_transition(
            ConfigEvent.VALIDATE, ConfigState.PARSED, ConfigState.VALIDATED
        )
        fsm_builder.add_transition(
            ConfigEvent.PROCESS, ConfigState.VALIDATED, ConfigState.PROCESSED
        )
        fsm_builder.add_transition(
            ConfigEvent.COMPLETE, ConfigState.PROCESSED, ConfigState.COMPLETED
        )
        return fsm_builder

    def start(self):
        self.fsm.trigger_event(ConfigEvent.READ)
        self.fsm.trigger_event(ConfigEvent.BUILD)
        self.fsm.trigger_event(ConfigEvent.PARSE)
        self.fsm.trigger_event(ConfigEvent.VALIDATE)
        self.fsm.trigger_event(ConfigEvent.PROCESS)
        self.fsm.trigger_event(ConfigEvent.COMPLETE)

    def do_read_configuration_file(self, e):
        config_dir = os.path.expanduser(
            os.path.join(self.args.base_directory + CONFIG_DIR)
        )

        # create configuration directory if it is not present
        # so that user can easily put his configuration there
        if config_dir and not os.path.exists(config_dir):
            logger.debug("Creating path '{}'".format(config_dir))
            os.makedirs(config_dir)

        config_file_path = self.get_baking_cfg_file(config_dir)

        logger.info("Loading baking configuration file {}".format(config_file_path))

        self.__config_text = ConfigParser.load_file(config_file_path)

    def do_build_parser(self, e):
        provider_factory = ProviderFactory(self.args.reward_data_provider)

        self.__parser = BakingYamlConfParser(
            yaml_text=self.__config_text,
            clnt_mngr=self.__node_client,
            provider_factory=provider_factory,
            network_config=self.__nw_cfg,
            node_url=self.args.node_endpoint,
            api_base_url=self.args.api_base_url,
        )

    def do_parse_cfg(self, e):
        self.__parser.parse()

    def do_validate_cfg(self, e):
        self.__parser.validate()

    def do_process_cfg(self, e):
        self.__parser.process()

    def get_conf(self):
        cfg_dict = self.__parser.get_conf_obj()
        return BakingConf(cfg_dict)

    @property
    def args(self):
        return self.__args

    @staticmethod
    def get_baking_cfg_file(cfg_dir):
        cfg_file = None
        for file in os.listdir(cfg_dir):
            if file.endswith(".yaml") and not file.startswith("master"):
                if cfg_file:
                    raise Exception(
                        "Application only supports one baking configuration file. Found at least 2 {}, {}".format(
                            cfg_file, file
                        )
                    )
                cfg_file = file

        if cfg_file is None:
            raise Exception(
                "Unable to find any '.yaml' configuration files inside configuration directory({})".format(
                    cfg_dir
                )
            )

        return os.path.join(cfg_dir, cfg_file)
