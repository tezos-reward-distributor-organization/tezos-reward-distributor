import yaml

from config.addr_type import AddrType
from config.yaml_conf_parser import YamlConfParser
from Constants import RewardsType, ALMOST_ZERO
from exception.configuration import ConfigurationException
from log_config import main_logger
from model.baking_conf import (
    FOUNDERS_MAP,
    OWNERS_MAP,
    BAKING_ADDRESS,
    SUPPORTERS_SET,
    SERVICE_FEE,
    FULL_SUPPORTERS_SET,
    MIN_DELEGATION_AMT,
    PAYMENT_ADDRESS,
    SPECIALS_MAP,
    DELEGATOR_PAYS_XFER_FEE,
    REACTIVATE_ZEROED,
    DELEGATOR_PAYS_RA_FEE,
    RULES_MAP,
    MIN_DELEGATION_KEY,
    TOF,
    TOB,
    TOE,
    EXCLUDED_DELEGATORS_SET_TOB,
    EXCLUDED_DELEGATORS_SET_TOE,
    EXCLUDED_DELEGATORS_SET_TOF,
    DEST_MAP,
    PLUGINS_CONF,
    DEXTER,
    CONTRACTS_SET,
    REWARDS_TYPE,
)
from util.address_validator import AddressValidator
from util.fee_validator import FeeValidator

logger = main_logger.getChild("config_parser")

PKH_LENGHT = 36


class BakingYamlConfParser(YamlConfParser):
    def __init__(
        self,
        yaml_text,
        clnt_mngr,
        provider_factory,
        network_config,
        node_url,
        block_api=None,
        api_base_url=None,
    ) -> None:
        super().__init__(yaml_text)
        self.clnt_mngr = clnt_mngr
        self.network_config = network_config
        if block_api is None:
            block_api = provider_factory.newBlockApi(
                network_config, node_url, api_base_url=api_base_url
            )
        self.block_api = block_api

    def parse(self):
        yaml_conf_dict = super().parse()
        self.set_conf_obj(yaml_conf_dict)

    def validate(self):
        conf_obj = self.get_conf_obj()
        self.validate_baking_address(conf_obj)
        self.validate_payment_address(conf_obj)
        self.validate_share_map(conf_obj, FOUNDERS_MAP)
        self.validate_share_map(conf_obj, OWNERS_MAP)
        self.validate_service_fee(conf_obj)
        self.validate_min_delegation_amt(conf_obj)
        self.validate_address_set(conf_obj, SUPPORTERS_SET)
        self.validate_specials_map(conf_obj)
        self.validate_dest_map(conf_obj)
        self.validate_plugins(conf_obj)
        self.validate_rewards_type(conf_obj)
        self.parse_bool(conf_obj, DELEGATOR_PAYS_XFER_FEE, True)
        self.parse_bool(conf_obj, REACTIVATE_ZEROED, None)
        self.parse_bool(conf_obj, DELEGATOR_PAYS_RA_FEE, None)

    def set(self, key, value):
        self.conf_obj[key] = value

    def process(self):
        conf_obj = self.get_conf_obj()

        conf_obj[FULL_SUPPORTERS_SET] = set(
            conf_obj[SUPPORTERS_SET]
            | set(conf_obj[FOUNDERS_MAP].keys())
            | set(conf_obj[OWNERS_MAP].keys())
        )

        conf_obj[EXCLUDED_DELEGATORS_SET_TOE] = set(
            [k for k, v in conf_obj[RULES_MAP].items() if v == TOE]
        )
        conf_obj[EXCLUDED_DELEGATORS_SET_TOF] = set(
            [k for k, v in conf_obj[RULES_MAP].items() if v == TOF]
        )
        conf_obj[EXCLUDED_DELEGATORS_SET_TOB] = set(
            [k for k, v in conf_obj[RULES_MAP].items() if v == TOB]
        )

        addr_validator = AddressValidator("dest_map")
        conf_obj[DEST_MAP] = {
            k: v for k, v in conf_obj[RULES_MAP].items() if addr_validator.isaddress(v)
        }

        conf_obj[CONTRACTS_SET] = set(
            [k for k, v in conf_obj[RULES_MAP].items() if v.lower() == DEXTER]
        )

        # default destination for min_delegation filtered account rewards
        if MIN_DELEGATION_KEY not in conf_obj[RULES_MAP]:
            conf_obj[EXCLUDED_DELEGATORS_SET_TOB].add(MIN_DELEGATION_KEY)

    def validate_share_map(self, conf_obj, map_name):
        """
        all shares in the map must sum up to 1
        :param conf_obj: configuration object
        :param map_name: name of the map to validate
        :return: None
        """

        if map_name not in conf_obj:
            conf_obj[map_name] = dict()
            return

        if not conf_obj[map_name]:
            conf_obj[map_name] = dict()
            return

        if isinstance(conf_obj[map_name], str) and conf_obj[map_name].lower() == "none":
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
                if abs(
                    1 - sum(share_map.values()) > ALMOST_ZERO
                ):  # a zero check actually
                    raise ConfigurationException(
                        "Map '{}' shares does not sum up to 1!".format(map_name)
                    )
            except TypeError:
                raise ConfigurationException(
                    "Map '{}' values must be number!".format(map_name)
                )

    def validate_service_fee(self, conf_obj):
        if SERVICE_FEE not in conf_obj:
            raise ConfigurationException("Service fee is not set")

        FeeValidator(SERVICE_FEE).validate(conf_obj[(SERVICE_FEE)])

    def validate_min_delegation_amt(self, conf_obj):
        if MIN_DELEGATION_AMT not in conf_obj:
            conf_obj[MIN_DELEGATION_AMT] = 0
            return

        if not self.validate_non_negative_int(conf_obj[MIN_DELEGATION_AMT]):
            raise ConfigurationException(
                "Invalid value:'{}'. {} parameter value must be an non negative integer".format(
                    conf_obj[MIN_DELEGATION_AMT], MIN_DELEGATION_AMT
                )
            )

    def validate_payment_address(self, conf_obj):
        if PAYMENT_ADDRESS not in conf_obj or not conf_obj[PAYMENT_ADDRESS]:
            raise ConfigurationException("Payment address must be set")

        pymnt_addr = conf_obj[(PAYMENT_ADDRESS)]

        if not pymnt_addr:
            raise ConfigurationException("Payment address must be set")

        if pymnt_addr.startswith("KT"):
            raise ConfigurationException(
                "KT addresses cannot be used for payments. Only tz addresses are allowed"
            )

        if len(pymnt_addr) == PKH_LENGHT and pymnt_addr.startswith("tz"):
            self.clnt_mngr.check_pkh_known_by_signer(pymnt_addr)

            conf_obj[("__%s_type" % PAYMENT_ADDRESS)] = AddrType.TZ
            conf_obj[("__%s_pkh" % PAYMENT_ADDRESS)] = pymnt_addr
            conf_obj[("__%s_manager" % PAYMENT_ADDRESS)] = pymnt_addr

        else:
            raise ConfigurationException(
                "Payment Address ({}) cannot be translated into a PKH. "
                "Make sure it is a tz1 address and to first import "
                "its corresponding secret key to the signer. ".format(pymnt_addr)
            )

    def validate_baking_address(self, conf_obj):
        if BAKING_ADDRESS not in conf_obj or not conf_obj[BAKING_ADDRESS]:
            raise ConfigurationException("Baking address must be set")

        baking_address = conf_obj[BAKING_ADDRESS]

        if baking_address.startswith("KT"):
            raise ConfigurationException(
                "KT addresses cannot act as bakers. Only tz addresses can be registered to bake."
            )

        # key_name must has a length of 36 and starts with tz an alias is not expected
        if len(baking_address) == PKH_LENGHT:
            if not baking_address.startswith("tz"):
                raise ConfigurationException(
                    "Baking address must be a valid tz address."
                )
            else:
                if not self.block_api.get_revelation(baking_address):
                    raise ConfigurationException(
                        "Baking address {} did not reveal key.".format(baking_address)
                    )

                if not self.block_api.get_delegatable(baking_address):
                    raise ConfigurationException(
                        "Baking address {} is not enabled for delegation".format(
                            baking_address
                        )
                    )
        else:
            raise ConfigurationException(
                "Baking address length must be {}".format(PKH_LENGHT)
            )

    def validate_specials_map(self, conf_obj):
        if SPECIALS_MAP not in conf_obj:
            conf_obj[SPECIALS_MAP] = dict()
            return

        if (
            isinstance(conf_obj[SPECIALS_MAP], str)
            and conf_obj[SPECIALS_MAP].lower() == "none"
        ):
            conf_obj[SPECIALS_MAP] = dict()
            return

        if not conf_obj[SPECIALS_MAP]:
            return

        addr_validator = AddressValidator(SPECIALS_MAP)
        for key, value in conf_obj[SPECIALS_MAP].items():
            addr_validator.validate(key)
            FeeValidator("specials_map:" + key).validate(value)

    def validate_address_set(self, conf_obj, set_name):
        if set_name not in conf_obj:
            conf_obj[set_name] = set()
            return

        if conf_obj[set_name] is None:
            conf_obj[set_name] = set()
            return

        if isinstance(conf_obj[set_name], str) and conf_obj[set_name].lower() == "none":
            conf_obj[set_name] = set()
            return

        # empty sets are evaluated as dict
        if not conf_obj[set_name] and (
            isinstance(conf_obj[set_name], dict) or isinstance(conf_obj[set_name], list)
        ):
            conf_obj[set_name] = set()
            return

        # {KT*****,KT****} are loaded as {KT*****:None,KT****:None}
        # convert to set
        if isinstance(conf_obj[set_name], dict) and set(
            conf_obj[set_name].values()
        ) == {None}:
            conf_obj[set_name] = set(conf_obj[set_name].keys())

        validator = AddressValidator(set_name)
        for addr in conf_obj[set_name]:
            validator.validate(addr)

    def validate_non_negative_int(self, param_value):
        try:
            param_value += 1
        except TypeError:
            return False

        param_value -= 1  # old value

        if param_value < 0:
            return False

        return True

    def validate_plugins(self, conf_obj):

        # if plugins config missing, then no plugins
        if PLUGINS_CONF not in conf_obj:
            conf_obj[PLUGINS_CONF] = {}

        if conf_obj[PLUGINS_CONF] is None or "enabled" not in conf_obj[PLUGINS_CONF]:
            conf_obj[PLUGINS_CONF] = {"enabled": None}

    def validate_rewards_type(self, conf_obj):

        if REWARDS_TYPE not in conf_obj or conf_obj[REWARDS_TYPE] is None:
            conf_obj[REWARDS_TYPE] = RewardsType.ACTUAL
            logger.warning(
                "[config_parser] Parameter '{:s}' is missing or incorrectly configured. "
                "Defaults to 'actual' rewards payout type.".format(REWARDS_TYPE)
            )

        if conf_obj[REWARDS_TYPE] == RewardsType.ESTIMATED:
            raise ConfigurationException(
                "Setting 'rewards_type' to 'estimated' is no longer supported.\n"
                "Please see https://tezos-reward-distributor-organization.github.io/tezos-reward-distributor/payouttiming.html\n"
                "for details on how to configure a improved method."
            )

        # Validate correct value
        try:
            v = conf_obj[REWARDS_TYPE]
            r_type = RewardsType(v)
        except ValueError:
            raise ConfigurationException(
                "'{:s}' is not a valid option for parameter '{:s}'. "
                "Please consult the documentation.".format(v, REWARDS_TYPE)
            )

        # Reset conf object to be the enum
        conf_obj[REWARDS_TYPE] = r_type

    def parse_bool(self, conf_obj, param_name, default):

        if param_name not in conf_obj:

            # If required param (ie: no default), raise exception if not defined
            if default is None:
                raise ConfigurationException(
                    "Parameter '{}' is not present in config file. Please consult the documentation and add this parameter.".format(
                        param_name
                    )
                )
            else:
                conf_obj[param_name] = default
                return

        # already a bool value
        if isinstance(conf_obj[param_name], bool):
            return

        if (
            isinstance(conf_obj[param_name], str)
            and "true" == conf_obj[param_name].lower()
        ):
            conf_obj[param_name] = True
        else:
            conf_obj[param_name] = False

    def validate_dest_map(self, conf_obj):
        if RULES_MAP not in conf_obj:
            conf_obj[RULES_MAP] = dict()
            return

        if (
            isinstance(conf_obj[RULES_MAP], str)
            and conf_obj[SPECIALS_MAP].lower() == "none"
        ):
            conf_obj[RULES_MAP] = dict()
            return

        if not conf_obj[RULES_MAP]:
            return

        addr_validator = AddressValidator(RULES_MAP)
        for key, value in conf_obj[RULES_MAP].items():
            # validate key (and address or MINDELEGATION)
            if key != MIN_DELEGATION_KEY:
                addr_validator.validate(key)
            # validate destination value (An address OR TOF OR TOB OR TOE)
            if value not in [TOF, TOB, TOE]:
                addr_validator.validate(key)


def rewardstype_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.add_representer(RewardsType, rewardstype_representer)
