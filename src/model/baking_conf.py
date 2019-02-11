import json

from config.yaml_baking_conf_parser import SERVICE_FEE, OWNERS_MAP, FOUNDERS_MAP, BAKING_ADDRESS, PAYMENT_ADDRESS, \
    PYMNT_SCALE, PRCNT_SCALE, EXCLUDED_DELEGATORS_SET, SPECIALS_MAP, SUPPORTERS_SET, FULL_SUPPORTERS_SET, \
    MIN_DELEGATION_AMT
from model.custom_json_encoder import CustomJsonEncoder


class BakingConf:
    def __init__(self, cfg_dict, master_dict=None) -> None:
        super().__init__()
        self.master_dict = master_dict
        self.cfg_dict = cfg_dict

    def get_attribute(self, attr):
        if attr in self.cfg_dict:
            return self.cfg_dict[attr]

        if self.master_dict and attr in self.master_dict:
            return self.master_dict[attr]

        raise Exception("Attribute {} not found in application configuration.".format(attr))

    def get_baking_address(self):
        return self.get_attribute(BAKING_ADDRESS)

    def get_payment_address(self):
        return self.get_attribute(PAYMENT_ADDRESS)

    def get_service_fee(self):
        return self.get_attribute(SERVICE_FEE)

    def get_owners_map(self):
        return self.get_attribute(OWNERS_MAP)

    def get_founders_map(self):
        return self.get_attribute(FOUNDERS_MAP)

    def get_specials_map(self):
        return self.get_attribute(SPECIALS_MAP)

    def get_excluded_delegators_set(self):
        return self.get_attribute(EXCLUDED_DELEGATORS_SET)

    def get_supporters_set(self):
        return self.get_attribute(SUPPORTERS_SET)

    def get_full_supporters_set(self):
        return self.get_attribute(FULL_SUPPORTERS_SET)

    def get_payment_scale(self):
        return self.get_attribute(PYMNT_SCALE)

    def get_percentage_scale(self):
        return self.get_attribute(PRCNT_SCALE)

    def get_min_delegation_amount(self):
        return self.get_attribute(MIN_DELEGATION_AMT)

    def __repr__(self) -> str:
        return json.dumps(self.__dict__, cls=CustomJsonEncoder, indent=1)

