import json
from util.address_validator import AddressValidator
from util.fee_validator import FeeValidator

PKH_LENGHT = 36

SERVICE_FEE = 'service_fee'
OWNERS_MAP = 'owners_map'
FOUNDERS_MAP = 'founders_map'
BAKING_ADDRESS = 'baking_address'
SPECIALS_MAP = 'specials_map'
RULES_MAP = 'rules_map'
SUPPORTERS_SET = 'supporters_set'
PAYMENT_ADDRESS = 'payment_address'
MIN_DELEGATION_AMT = 'min_delegation_amt'
REACTIVATE_ZEROED = 'reactivate_zeroed'
DELEGATOR_PAYS_XFER_FEE = 'delegator_pays_xfer_fee'
DELEGATOR_PAYS_RA_FEE = 'delegator_pays_ra_fee'

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


class BakingConf:
    def __init__(self, cfg_dict, master_dict=None) -> None:
        super().__init__()
        self.master_dict = master_dict
        self.cfg_dict = cfg_dict

    def process(self):

        self.cfg_dict[FULL_SUPPORTERS_SET] = set(
            self.cfg_dict[SUPPORTERS_SET] | set(self.cfg_dict[FOUNDERS_MAP].keys()) | set(self.cfg_dict[OWNERS_MAP].keys()))

        self.cfg_dict[EXCLUDED_DELEGATORS_SET_TOE] = set([k for k, v in self.cfg_dict[RULES_MAP].items() if v == TOE])
        self.cfg_dict[EXCLUDED_DELEGATORS_SET_TOF] = set([k for k, v in self.cfg_dict[RULES_MAP].items() if v == TOF])
        self.cfg_dict[EXCLUDED_DELEGATORS_SET_TOB] = set([k for k, v in self.cfg_dict[RULES_MAP].items() if v == TOB])

        addr_validator = AddressValidator("dest_map")
        self.cfg_dict[DEST_MAP] = {k: v for k, v in self.cfg_dict[RULES_MAP].items() if addr_validator.isaddress(v)}

        # default destination for min_delegation filtered account rewards
        if MIN_DELEGATION_KEY not in self.cfg_dict[RULES_MAP]:
            self.cfg_dict[EXCLUDED_DELEGATORS_SET_TOB].add(MIN_DELEGATION_KEY)

    def validate(self, _wallet_client_manager, _block_api):

        self.validate_baking_address()
        self.validate_payment_address(_wallet_client_manager, _block_api)
        self.validate_share_map(FOUNDERS_MAP)
        self.validate_share_map(OWNERS_MAP)
        self.validate_service_fee()
        self.validate_min_delegation_amt()
        self.validate_address_set(SUPPORTERS_SET)
        self.validate_specials_map()
        self.validate_dest_map()
        self.parse_bool(DELEGATOR_PAYS_XFER_FEE, True)
        self.parse_bool(REACTIVATE_ZEROED, None)
        self.parse_bool(DELEGATOR_PAYS_RA_FEE, None)

    def validate_baking_address(self):
        if BAKING_ADDRESS not in self.cfg_dict or not self.cfg_dict[BAKING_ADDRESS]:
            raise ConfigurationException("Baking address must be set")

        baking_address = self.cfg_dict[BAKING_ADDRESS]

        # key_name must has a length of 36 and starts with tz or KT, an alias is not expected
        if len(baking_address) == PKH_LENGHT:
            if not baking_address.startswith("dn"):
                raise ConfigurationException("Baking address must be a valid dn address")
        else:
            raise ConfigurationException("Baking address length must be {}".format(PKH_LENGHT))

        pass

    def validate_payment_address(self, wllt_clnt_mngr, block_api):
        if PAYMENT_ADDRESS not in self.cfg_dict or not self.cfg_dict[PAYMENT_ADDRESS]:
            raise ConfigurationException("Payment address must be set")

        pymnt_addr = self.cfg_dict[(PAYMENT_ADDRESS)]

        if not pymnt_addr:
            raise ConfigurationException("Payment address must be set")

        if pymnt_addr.startswith("KT1"):
            raise ConfigurationException("KT1 addresses cannot be used for payments. Only dn addresses are allowed.")
        
        if len(pymnt_addr) == PKH_LENGHT and pymnt_addr.startswith("dn"):

            addr_obj = wllt_clnt_mngr.get_addr_dict_by_pkh(pymnt_addr)

            self.check_sk(addr_obj, pymnt_addr)

            self.cfg_dict[('__%s_pkh' % PAYMENT_ADDRESS)] = pymnt_addr
            self.cfg_dict[('__%s_manager' % PAYMENT_ADDRESS)] = pymnt_addr

        else:
            if pymnt_addr in wllt_clnt_mngr.get_known_contracts_by_alias():
                pkh = wllt_clnt_mngr.get_known_contract_by_alias(pymnt_addr)

                if pkh.startswith("KT1"):
                    raise ConfigurationException("KT1 addresses cannot be used for payments. Only dn addresses are allowed.")

                addr_obj = wllt_clnt_mngr.get_addr_dict_by_pkh(pkh)

                self.check_sk(addr_obj, pkh)

                self.cfg_dict[('__%s_pkh' % PAYMENT_ADDRESS)] = pkh
                self.cfg_dict[('__%s_manager' % PAYMENT_ADDRESS)] = wllt_clnt_mngr.get_manager_for_contract(pkh)

            else:
                raise ConfigurationException("Payment Address ({}) cannot be translated into a PKH or alias. "
                                             "If it is an alias import it first. ".format(pymnt_addr))

        # if reveal information is present, do not ask
        if 'revealed' in addr_obj:
            revealed = addr_obj['revealed']
        else:
            revealed = block_api.get_revelation(self.cfg_dict[('__%s_pkh' % PAYMENT_ADDRESS)])

        # payment address needs to be revealed
        if not revealed:
            raise ConfigurationException("Payment Address ({0}) is not eligible for payments as the public key is not revealed.\n"
                                         "Use command 'tezos-client reveal key for {0}' to reveal your public key.\n"
                                         "For more information please refer to tezos command line interface."
                                         .format(pymnt_addr))

    def validate_share_map(self, map_name):
        """
        all shares in the map must sum up to 1
        :param self.cfg_dict: configuration object
        :param map_name: name of the map to validate
        :return: None
        """

        if map_name not in self.cfg_dict:
            self.cfg_dict[map_name] = dict()
            return

        if not self.cfg_dict[map_name]:
            self.cfg_dict[map_name] = dict()
            return

        if isinstance(self.cfg_dict[map_name], str) and self.cfg_dict[map_name].lower() == 'none':
            self.cfg_dict[map_name] = dict()
            return

        if not self.cfg_dict[map_name]:
            return

        share_map = self.cfg_dict[map_name]

        validator = AddressValidator(map_name)
        for key, value in share_map.items():
            validator.validate(key)

        if len(share_map) > 0:
            try:
                if abs(1 - sum(share_map.values()) > 1e-4):  # a zero check actually
                    raise ConfigurationException("Map '{}' shares does not sum up to 1!".format(map_name))
            except TypeError:
                raise ConfigurationException("Map '{}' values must be number!".format(map_name))

    def validate_service_fee(self):
        if SERVICE_FEE not in self.cfg_dict:
            raise ConfigurationException("Service fee is not set")
        FeeValidator(SERVICE_FEE).validate(self.cfg_dict[(SERVICE_FEE)])

    def validate_min_delegation_amt(self):
        if MIN_DELEGATION_AMT not in self.cfg_dict:
            self.cfg_dict[MIN_DELEGATION_AMT] = 0
            return

        if not self.validate_non_negative_int(self.cfg_dict[MIN_DELEGATION_AMT]):
            raise ConfigurationException("Invalid value:'{}'. {} parameter value must be an non negative integer".
                                         format(self.cfg_dict[MIN_DELEGATION_AMT], MIN_DELEGATION_AMT))

    def validate_address_set(self, set_name):
        if set_name not in self.cfg_dict:
            self.cfg_dict[set_name] = set()
            return

        if isinstance(self.cfg_dict[set_name], str) and self.cfg_dict[set_name].lower() == 'none':
            self.cfg_dict[set_name] = set()
            return

        # empty sets are evaluated as dict
        if not self.cfg_dict[set_name] and (isinstance(self.cfg_dict[set_name], dict) or isinstance(self.cfg_dict[set_name], list)):
            self.cfg_dict[set_name] = set()
            return

        # {KT*****,KT****} are loaded as {KT*****:None,KT****:None}
        # convert to set
        if isinstance(self.cfg_dict[set_name], dict) and set(self.cfg_dict[set_name].values()) == {None}:
            self.cfg_dict[set_name] = set(self.cfg_dict[set_name].keys())

        validator = AddressValidator(set_name)
        for addr in self.cfg_dict[set_name]:
            validator.validate(addr)

    def validate_specials_map(self):
        if SPECIALS_MAP not in self.cfg_dict:
            self.cfg_dict[SPECIALS_MAP] = dict()
            return

        if isinstance(self.cfg_dict[SPECIALS_MAP], str) and self.cfg_dict[SPECIALS_MAP].lower() == 'none':
            self.cfg_dict[SPECIALS_MAP] = dict()
            return

        if not self.cfg_dict[SPECIALS_MAP]:
            return

        addr_validator = AddressValidator(SPECIALS_MAP)
        for key, value in self.cfg_dict[SPECIALS_MAP].items():
            addr_validator.validate(key)
            FeeValidator("specials_map:" + key).validate(value)

    def validate_dest_map(self):
        if RULES_MAP not in self.cfg_dict:
            self.cfg_dict[RULES_MAP] = dict()
            return

        if isinstance(self.cfg_dict[RULES_MAP], str) and self.cfg_dict[SPECIALS_MAP].lower() == 'none':
            self.cfg_dict[RULES_MAP] = dict()
            return

        if not self.cfg_dict[RULES_MAP]:
            return

        addr_validator = AddressValidator(RULES_MAP)
        for key, value in self.cfg_dict[RULES_MAP].items():
            # validate key (and address or MINDELEGATION)
            if key != MIN_DELEGATION_KEY:
                addr_validator.validate(key)
            # validate destination value (An address OR TOF OR TOB OR TOE)
            if value not in [TOF, TOB, TOE]:
                addr_validator.validate(key)

    def parse_bool(self, param_name, default):
        if param_name not in self.cfg_dict:
            # If required param (ie: no default), raise exception if not defined
            if default is None:
                raise ConfigurationException("Parameter '{}' is not present in config file. Please consult the documentation and add this parameter.".format$
            self.cfg_dict[param_name] = default
            return

        # already a bool value
        if type(self.cfg_dict[param_name]) == type(False):
            return

        if isinstance(self.cfg_dict[param_name], str) and "true" == self.cfg_dict[param_name].lower():
            self.cfg_dict[param_name] = True
        else:
            self.cfg_dict[param_name] = False

    def check_sk(self, addr_obj, pkh):
        if not addr_obj['sk']:
            raise ConfigurationException("No secret key for Address Obj {} with PKH {}".format(addr_obj, pkh))

    def validate_non_negative_int(self, param_value):
        try:
            param_value += 1
        except TypeError:
            return False

        param_value -= 1  # old value

        if param_value < 0:
            return False

        return True

    def set(self, key, value):
        self.cfg_dict[key] = value

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

    def get_reactivate_zeroed(self):
        return self.get_attribute(REACTIVATE_ZEROED)

    def get_delegator_pays_xfer_fee(self):
        return self.get_attribute(DELEGATOR_PAYS_XFER_FEE)

    def get_delegator_pays_ra_fee(self):
        return self.get_attribute(DELEGATOR_PAYS_RA_FEE)

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

    def toDB(self):
        # Return a dictionary for DB storage without '__' keys
        db_dict = {}
        for k in self.cfg_dict:
            if k[:2] != '__':
                db_dict[k] = self.cfg_dict[k]
        return db_dict

    def __repr__(self) -> str:
        return json.dumps(self.__dict__, cls=BakingConfJsonEncoder, indent=1)


class BakingConfJsonEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, set):
            # Convert set() to list
            return list(obj)
	    return json.JSONEncoder.default(self, obj)


class ConfigurationException(Exception):
    pass
