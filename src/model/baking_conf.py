import json

SERVICE_FEE = 'service_fee'
OWNERS_MAP = 'owners_map'
FOUNDERS_MAP = 'founders_map'
BAKING_ADDRESS = 'baking_address'
SPECIALS_MAP = 'specials_map'
RULES_MAP = 'rules_map'
SUPPORTERS_SET = 'supporters_set'
PAYMENT_ADDRESS = 'payment_address'
MIN_DELEGATION_AMT = 'min_delegation_amt'
DELEGATOR_PAYS_XFER_FEE = 'delegator_pays_xfer_fee'
### extensions
FULL_SUPPORTERS_SET = "__full_supporters_set"
EXCLUDED_DELEGATORS_SET_TOB = "__excluded_delegators_set_tob"
EXCLUDED_DELEGATORS_SET_TOE = "__excluded_delegators_set_toe"
EXCLUDED_DELEGATORS_SET_TOF = "__excluded_delegators_set_tof"
DEST_MAP = "__destination_map"

### destination map
TOF = "TOF"
TOB = "TOB"
TOE = "TOE"
MIN_DELEGATION_KEY = 'mindelegation'
###

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

    def get_supporters_set(self):
        return self.get_attribute(SUPPORTERS_SET)

    def get_full_supporters_set(self):
        return self.get_attribute(FULL_SUPPORTERS_SET)

    def get_min_delegation_amount(self):
        return self.get_attribute(MIN_DELEGATION_AMT)

    def get_delegator_pays_xfer_fee(self):
        return self.get_attribute(DELEGATOR_PAYS_XFER_FEE)

    def get_rule_map(self):
        return self.get_attribute(RULES_MAP)

    def get_dest_map(self):
        return self.get_attribute(DEST_MAP)

    def get_excluded_set_toe(self):
        return self.get_attribute(EXCLUDED_DELEGATORS_SET_TOE)

    def get_excluded_set_tob(self):
        return self.get_attribute(EXCLUDED_DELEGATORS_SET_TOB)

    def get_excluded_set_tof(self):
        return self.get_attribute(EXCLUDED_DELEGATORS_SET_TOF)

    def __repr__(self) -> str:
        return json.dumps(self.__dict__, cls=CustomJsonEncoder, indent=1)
