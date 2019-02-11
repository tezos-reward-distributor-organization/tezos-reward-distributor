from config.addr_type import AddrType
from config.yaml_conf_parser import YamlConfParser
from util.address_validator import AddressValidator
from util.fee_validator import FeeValidator

SERVICE_FEE = 'service_fee'
OWNERS_MAP = 'owners_map'
FOUNDERS_MAP = 'founders_map'
BAKING_ADDRESS = 'baking_address'
PRCNT_SCALE = "prcnt_scale"
PYMNT_SCALE = "pymnt_scale"
EXCLUDED_DELEGATORS_SET = "excluded_delegators_set"
SPECIALS_MAP = 'specials_map'
SUPPORTERS_SET = 'supporters_set'
PAYMENT_ADDRESS = 'payment_address'
MIN_DELEGATION_AMT = 'min_delegation_amt'
### extensions
FULL_SUPPORTERS_SET = "full_supporters_set"

PKH_LENGHT = 36


class BakingYamlConfParser(YamlConfParser):
    def __init__(self, yaml_text, wllt_clnt_mngr, verbose=None) -> None:
        super().__init__(yaml_text, verbose)
        self.wllt_clnt_mngr = wllt_clnt_mngr

    def parse(self):
        yaml_conf_dict = super().parse()
        self.set_conf_obj(yaml_conf_dict)

    def validate(self):
        conf_obj = self.get_conf_obj()
        self.__validate_share_map(conf_obj, FOUNDERS_MAP)
        self.__validate_share_map(conf_obj, OWNERS_MAP)
        self.__validate_service_fee(conf_obj)
        self.__validate_baking_address(conf_obj[BAKING_ADDRESS])
        self.__validate_payment_address(conf_obj)
        self.__validate_min_delegation_amt(conf_obj)
        self.__validate_address_set(conf_obj, SUPPORTERS_SET)
        self.__validate_address_set(conf_obj, EXCLUDED_DELEGATORS_SET)
        self.__validate_specials_map(conf_obj)
        self.__validate_scale(conf_obj, PYMNT_SCALE)
        self.__validate_scale(conf_obj, PRCNT_SCALE)

    def process(self):
        conf_obj = self.get_conf_obj()
        conf_obj[SERVICE_FEE] = conf_obj[SERVICE_FEE] / 100.0
        conf_obj[(FULL_SUPPORTERS_SET)] = conf_obj[SUPPORTERS_SET] | set(conf_obj[FOUNDERS_MAP].keys()) | set(
            conf_obj[OWNERS_MAP].keys())

    def __validate_share_map(self, conf_obj, map_name):
        """
        all shares in the map must sum up to 1
        :param conf_obj: configuration object
        :param map_name: name of the map to validate
        :return: None
        """

        if map_name not in conf_obj:
            conf_obj[map_name] = dict()
            return

        if isinstance(conf_obj[map_name], str) and conf_obj[map_name].lower() == 'none':
            conf_obj[map_name] = dict()
            return

        if not conf_obj[map_name]:
            return

        share_map = conf_obj[map_name]

        validator = AddressValidator(map_name)
        for key, value in share_map.items():
            validator.validate(key)

        if len(share_map) > 0:
            try:
                if abs(1 - sum(share_map.values()) > 1e-4):  # a zero check actually
                    raise Exception("Map '{}' shares does not sum up to 1!".format(map_name))
            except TypeError:
                raise Exception("Map '{}' values must be number!".format(map_name))

    def __validate_service_fee(self, conf_obj):
        if SERVICE_FEE not in conf_obj:
            raise Exception("Service fee is not set")

        FeeValidator(SERVICE_FEE).validate(conf_obj[(SERVICE_FEE)])

    def __validate_min_delegation_amt(self, conf_obj):
        if MIN_DELEGATION_AMT not in conf_obj:
            conf_obj[MIN_DELEGATION_AMT] = 0
            return

        if not self.__validate_non_negative_int(conf_obj[MIN_DELEGATION_AMT]):
            raise Exception("Invalid value:'{}'. {} parameter value must be an non negative integer".
                            format(conf_obj[MIN_DELEGATION_AMT], MIN_DELEGATION_AMT))

    def __validate_payment_address(self, conf_obj):
        pymnt_addr = conf_obj[(PAYMENT_ADDRESS)]

        if not pymnt_addr:
            raise Exception("Payment address must be set")

        if len(pymnt_addr) == PKH_LENGHT and (pymnt_addr.startswith("KT") or pymnt_addr.startswith("tz")):
            conf_obj[('%s_type' % PAYMENT_ADDRESS)] = AddrType.KT if pymnt_addr.startswith("KT") else AddrType.TZ
            conf_obj[('%s_pkh' % PAYMENT_ADDRESS)] = pymnt_addr
            conf_obj[('%s_manager' % PAYMENT_ADDRESS)] = self.wllt_clnt_mngr.get_manager_for_contract(pymnt_addr)
        else:
            if pymnt_addr in self.wllt_clnt_mngr.get_known_contacts_by_alias():
                pkh = self.wllt_clnt_mngr.get_known_contact_by_alias(pymnt_addr)

                conf_obj[('%s_type' % PAYMENT_ADDRESS)] = AddrType.KTALS if pkh.startswith("KT") else AddrType.TZALS
                conf_obj[('%s_pkh' % PAYMENT_ADDRESS)] = pkh
                conf_obj[('%s_manager' % PAYMENT_ADDRESS)] = self.wllt_clnt_mngr.get_manager_for_contract(pkh)

            else:
                raise Exception("Payment Address ({}) cannot be translated into a PKH or alias".format(pymnt_addr))

    def __validate_baking_address(self, baking_address):

        if not baking_address:
            raise Exception("Baking address must be set")

        # key_name must has a length of 36 and starts with tz or KT, an alias is not expected
        if len(baking_address) == PKH_LENGHT:
            if not baking_address.startswith("tz"):
                raise Exception("Baking address must be a valid tz address")
        else:
            raise Exception("Baking address length must be {}".format(PKH_LENGHT))

        pass

    def __validate_specials_map(self, conf_obj):
        if SPECIALS_MAP not in conf_obj:
            conf_obj[SPECIALS_MAP] = dict()
            return

        if isinstance(conf_obj[SPECIALS_MAP], str) and conf_obj[SPECIALS_MAP].lower() == 'none':
            conf_obj[SPECIALS_MAP] = dict()
            return

        if not conf_obj[SPECIALS_MAP]:
            return

        addr_validator = AddressValidator(SPECIALS_MAP)
        for key, value in conf_obj[SPECIALS_MAP].items():
            addr_validator.validate(key)
            FeeValidator(key).validate(value)

    def __validate_address_set(self, conf_obj, set_name):
        if set_name not in conf_obj:
            conf_obj[set_name] = set()
            return

        if isinstance(conf_obj[set_name], str) and conf_obj[set_name].lower() == 'none':
            conf_obj[set_name] = set()
            return

        if not conf_obj[set_name]:  # empty sets are evaluated as dict
            conf_obj[set_name] = set()
            return

        validator = AddressValidator(set_name)
        for addr in conf_obj[set_name]:
            validator.validate(addr)

    def __validate_scale(self, conf_obj, scale_name):
        if scale_name not in conf_obj:
            conf_obj[scale_name] = None
            return

        if isinstance(conf_obj[scale_name], str) and conf_obj[scale_name].lower() == 'none':
            conf_obj[scale_name] = None
            return

        if conf_obj[scale_name] is None:
            return

        if not self.__validate_non_negative_int(conf_obj[scale_name]):
            raise Exception("Invalid value:'{}'. {} parameter value must be an non negative integer or None. ".
                            format(conf_obj[scale_name], scale_name))

    def __validate_non_negative_int(self, param_value):
        try:
            param_value += 1
        except TypeError:
            return False

        param_value -= 1  # old value

        if param_value < 0:
            return False

        return True
