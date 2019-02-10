from abc import ABC, abstractmethod


class ConfigParser(ABC):
    def __init__(self, text, verbose=None):
        super(ConfigParser, self).__init__()
        self.conf_text = text
        self.verbose = verbose
        self.conf_obj = None

    @abstractmethod
    def parse(self):
        pass

    @abstractmethod
    def validate(self):
        pass

    @staticmethod
    def load_file(conf_file_path):
        with open(conf_file_path, 'r') as file:
            return file.readlines()

    def set_conf_obj(self, conf_obj):
        self.conf_obj = conf_obj

    def get_conf_obj(self):
        return self.conf_obj

    def get_conf_obj_attr(self, attr):
        return self.conf_obj[attr]
