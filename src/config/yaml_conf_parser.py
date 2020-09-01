import yaml

from config.config_parser import ConfigParser


class YamlConfParser(ConfigParser):
    def __init__(self, yaml_text, verbose=None) -> None:
        super().__init__(yaml_text, verbose)

    def parse(self):
        self.set_conf_obj(yaml.safe_load(self.conf_text))

        return self.get_conf_obj()

    def validate(self):
        return True

    def process(self):
        pass
