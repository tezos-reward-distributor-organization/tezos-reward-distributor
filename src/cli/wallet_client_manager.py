from cli.simple_client_manager import SimpleClientManager
from util.address_validator import AddressValidator
from util.client_utils import clear_terminal_chars, not_indicator_line


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

        response = self.send_request(" get manager for " + pkh)

        response = clear_terminal_chars(response)

        manager = self.parse_get_manager_for_contract_response(response)

        try:
            AddressValidator("manager").validate(manager)
        except Exception as e:
            raise Exception("Invalid response from client '{}'".format(response),e)
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
            print("Manager address is : {}".format(manager))

        return manager

    def generate_address_dict(self):
        if self.address_dict is not None:
            return self.address_dict

        self.address_dict = {}

        if self.contr_dict_by_alias is None:
            self.contr_dict_by_alias = self.__list_known_contracts_by_alias()

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        for pkh, dict_alias_sk in self.addr_dict_by_pkh.items():
            self.address_dict[pkh] = {"pkh": pkh, "originated": False, "alias": dict_alias_sk['alias'],
                                      "sk": dict_alias_sk['sk'], "manager": pkh}

        for alias, pkh in self.contr_dict_by_alias.items():
            if pkh.startswith("KT"):
                manager = self.get_manager_for_contract(pkh)
                manager_sk = self.addr_dict_by_pkh[manager]['sk']

                self.address_dict[pkh] = {"pkh": pkh, "originated": True, "alias": alias, "sk": manager_sk,
                                          "manager": manager}

    def __list_known_contracts_by_alias(self):
        response = self.send_request(" list known contracts")

        response = clear_terminal_chars(response)

        dict = self.__parse_list_known_contracts_response(response)

        return dict



    def __list_known_addresses_by_pkh(self):

        response = self.send_request(" list known addresses")

        response = clear_terminal_chars(response)

        dict = self.__parse_list_known_addresses_response(response)

        return dict

    def get_known_contract_by_alias(self, alias):

        if self.contr_dict_by_alias is None:
            self.contr_dict_by_alias = self.__list_known_contracts_by_alias()

        if alias not in self.contr_dict_by_alias:
            raise Exception("Alias {} is not imported to client. Import it first.".format(alias))

        return self.contr_dict_by_alias[alias]

    def get_known_contracts_by_alias(self):

        if self.contr_dict_by_alias is None:
            self.contr_dict_by_alias = self.__list_known_contracts_by_alias()

        return self.contr_dict_by_alias

    def get_known_addr_by_pkh(self, pkh):

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        if pkh not in self.addr_dict_by_pkh:
            raise Exception("Address {} is not imported to client. Import it first.".format(pkh))

        return self.addr_dict_by_pkh[pkh]

    def get_known_addrs_by_pkh(self):

        if self.addr_dict_by_pkh is None:
            self.addr_dict_by_pkh = self.__list_known_addresses_by_pkh()

        return self.addr_dict_by_pkh


    def __parse_list_known_addresses_response(self, response):
        dict = {}

        for line in response.splitlines():
            line = line.strip()
            if ":" in line and not_indicator_line(line):
                alias, pkh_plus_braces = line.split(":", maxsplit=1)
                pkh_plus_braces = pkh_plus_braces.replace(' (', ':')
                pkh, sk_section = pkh_plus_braces.split(":", maxsplit=1)
                sk_known = "sk known" in sk_section
                pkh = pkh.strip()
                alias = alias.strip()
                dict[pkh] = {"alias": alias, "sk": sk_known}

        if self.verbose:
            print("known addresses: {}".format(dict))

        return dict

    def __parse_list_known_contracts_response(self, response):
        dict = {}
        for line in response.splitlines():
            line = line.strip()
            if ":" in line and not_indicator_line(line):
                alias, pkh = line.split(":", maxsplit=1)
                dict[alias.strip()] = pkh.strip()
        if self.verbose:
            print("known contracts: {}".format(dict))
        return dict