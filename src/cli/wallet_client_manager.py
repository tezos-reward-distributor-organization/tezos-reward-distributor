from cli.simple_client_manager import SimpleClientManager
from exception.client import ClientException
from log_config import main_logger
from util.address_validator import AddressValidator
from util.client_utils import not_indicator_line

logger = main_logger


class WalletClientManager(SimpleClientManager):

    def __init__(self, client_path, contr_dict_by_alias=None,
                 addr_dict_by_pkh=None, managers=None, verbose=None) -> None:
        super().__init__(client_path, verbose)

        self.managers = managers
        if self.managers is None:
            self.managers = dict()

        self.contr_dict_by_alias = contr_dict_by_alias
        self.addr_dict_by_pkh = addr_dict_by_pkh
        self.address_dict = None

    def get_manager_for_contract(self, pkh):

        if pkh.startswith('tz'):
            return pkh

        if pkh in self.managers:
            return self.managers[pkh]

        _, response = self.send_request(" get manager for " + pkh)

        manager = self.parse_get_manager_for_contract_response(response)

        try:
            AddressValidator("manager").validate(manager)
        except Exception as e:
            raise ClientException("Invalid response from client '{}'".format(response), e)
        self.managers[pkh] = manager

        return manager

    def parse_get_manager_for_contract_response(self, response):
        manager = None
        for line in response.splitlines():
            line = line.strip()
            if line.startswith("tz"):
                line = line.replace(" (", ':')
                manager, alias_plus = line.split(":", maxsplit=1)
                break

        if self.verbose:
            logger.debug("Manager address is : {}".format(manager))

        return manager

    def get_addr_dict(self):
        if not self.address_dict:
            self.generate_address_dict()

        return self.address_dict

    def get_addr_dict_by_pkh(self, pkh):
        if not self.address_dict:
            self.generate_address_dict()

        if pkh not in self.address_dict:
            raise ClientException("Address(PKH) {} is not imported to client. Import it first.".format(pkh))

        return self.address_dict[pkh]

    def generate_address_dict(self):
        if self.address_dict is not None:
            return self.address_dict

        logger.debug("Generating known address dictionary")

        self.address_dict = {}

        #if self.contr_dict_by_alias is None:
        #    self.contr_dict_by_alias = self.__list_known_contracts_by_alias()

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        for pkh, dict_alias_sk in self.addr_dict_by_pkh.items():
            self.address_dict[pkh] = {"pkh": pkh, "originated": False, "alias": dict_alias_sk['alias'],
                                      "sk": dict_alias_sk['sk'], "manager": pkh}
            if 'revealed' in dict_alias_sk:
                self.address_dict[pkh]["revealed"] = dict_alias_sk['revealed']

            logger.debug("Known address added: {}".format(self.address_dict[pkh]))

        #for alias, pkh in self.contr_dict_by_alias.items():
        #    if pkh.startswith("KT"):
        #        manager = self.get_manager_for_contract(pkh)
        #        if manager not in self.addr_dict_by_pkh:
        #            # raise ConfigurationException("Manager pkh {} not found in known addresses".format(manager))
        #            manager_sk = None
        #        else:
        #            manager_sk = self.addr_dict_by_pkh[manager]['sk']

        #        self.address_dict[pkh] = {"pkh": pkh, "originated": True, "alias": alias, "sk": manager_sk, "manager": manager}
        #        if pkh in self.addr_dict_by_pkh and "revealed" in self.addr_dict_by_pkh[pkh]:
        #            self.address_dict[pkh]["revealed"] = self.addr_dict_by_pkh[pkh]["revealed"]

        #        logger.debug("Known contract added: {}".format(self.address_dict[pkh]))

        if not self.address_dict:
            logger.warn("No known address info is reached. Check your environment. Try to run in privileged mode.")

    def __list_known_contracts_by_alias(self):
        _, response = self.send_request(" list known contracts")

        dict = self.parse_list_known_contracts_response(response)

        for alias, pkh in dict.items():
            try:
                AddressValidator("known_contract").validate(pkh)
            except Exception as e:
                raise ClientException("Invalid response from client '{}'".format(response), e)

        return dict

    def __list_known_addresses_by_pkh(self):

        _, response = self.send_request(" list known addresses")

        dict = self.parse_list_known_addresses_response(response)

        for pkh, dict_alias_sk in dict.items():
            try:
                AddressValidator("known_address").validate(pkh)
            except Exception as e:
                raise ClientException("Invalid response from client '{}'".format(response), e)


        return dict

    def get_known_contract_by_alias(self, alias):

        if self.contr_dict_by_alias is None:
            self.contr_dict_by_alias = self.__list_known_contracts_by_alias()

        if alias not in self.contr_dict_by_alias:
            raise ClientException("Alias {} is not imported to client. Import it first.".format(alias))

        return self.contr_dict_by_alias[alias]

    def get_known_contracts_by_alias(self):

        if self.contr_dict_by_alias is None:
            self.contr_dict_by_alias = self.__list_known_contracts_by_alias()

        return self.contr_dict_by_alias

    def get_known_addr_by_pkh(self, pkh):

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        if pkh not in self.addr_dict_by_pkh:
            raise ClientException("Address(PKH) {} is not imported to client. Import it first.".format(pkh))

        return self.addr_dict_by_pkh[pkh]

    def has_known_addr_by_pkh(self, pkh):

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        return pkh in self.addr_dict_by_pkh

    def get_known_addrs_by_pkh(self):

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        return self.addr_dict_by_pkh

    def parse_list_known_addresses_response(self, response):
        dict = {}

        for line in response.splitlines():
            line = line.strip()
            if ":" in line and not_indicator_line(line):
                alias, pkh_plus_braces = line.split(":", maxsplit=1)
                pkh_plus_braces = pkh_plus_braces.replace(' (', ':')
                if ':' in pkh_plus_braces:
                    pkh, sk_section = pkh_plus_braces.split(":", maxsplit=1)
                else:
                    pkh = pkh_plus_braces.strip()
                    sk_section = ""
                sk_known = "sk known" in sk_section
                pkh = pkh.strip()
                alias = alias.strip()
                dict[pkh] = {"alias": alias, "sk": sk_known}

        if self.verbose:
            logger.debug("known addresses: {}".format(dict))

        return dict

    def parse_list_known_contracts_response(self, response):
        dict = {}
        for line in response.splitlines():
            line = line.strip()
            if ":" in line and not_indicator_line(line):
                alias, pkh = line.split(":", maxsplit=1)
                dict[alias.strip()] = pkh.strip()
        if self.verbose:
            logger.debug("known contracts: {}".format(dict))
        return dict
