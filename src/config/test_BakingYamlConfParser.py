from unittest import TestCase

from config.addr_type import AddrType
from config.yaml_baking_conf_parser import BakingYamlConfParser


class TestYamlAppConfParser(TestCase):
    def test_validate(self):
        data_fine = """
        version : 1.0
        baking_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        payment_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        founders_map : {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5}
        owners_map : {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5}
        service_fee : 4.53  
        """

        managers = {'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj'}
        cnf_prsr = BakingYamlConfParser(data_fine, dict(), managers)
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(cnf_prsr.get_conf_obj_attr('baking_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_pkh'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_manager'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_type'), AddrType.TZ)
        self.assertEqual(0, cnf_prsr.get_conf_obj_attr('min_delegation_amt'))
        self.assertEqual(cnf_prsr.get_conf_obj_attr('excluded_delegators_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('prcnt_scale'), None)
        self.assertEqual(cnf_prsr.get_conf_obj_attr('pymnt_scale'), None)

    def test_validate_no_founders_map(self):
        data_no_founders = """
        version : 1.0
        baking_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        payment_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        owners_map : {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5}
        service_fee : 4.5  
        """

        managers_map = {'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj'}
        cnf_prsr = BakingYamlConfParser(data_no_founders, dict(), managers_map)
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(cnf_prsr.get_conf_obj_attr('baking_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_pkh'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_manager'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_type'), AddrType.TZ)
        self.assertEqual(cnf_prsr.get_conf_obj_attr('founders_map'), dict())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('specials_map'), dict())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('supporters_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('excluded_delegators_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('prcnt_scale'), None)
        self.assertEqual(cnf_prsr.get_conf_obj_attr('pymnt_scale'), None)
        self.assertEqual(0, cnf_prsr.get_conf_obj_attr('min_delegation_amt'))

    def test_validate_pymnt_alias(self):
        data_no_founders = """
        version : 1.0
        baking_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        payment_address : ktPay
        owners_map : {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5}
        service_fee : 4.5  
        min_delegation_amt : 100
        """

        managers_map = {'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj',
                        'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj'}

        known_contracts = {'ktPay': 'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj'}

        cnf_prsr = BakingYamlConfParser(data_no_founders, known_contracts, managers_map)
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(cnf_prsr.get_conf_obj_attr('baking_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address'), 'ktPay')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_pkh'), 'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_manager'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_type'), AddrType.KTALS)

        self.assertEqual(cnf_prsr.get_conf_obj_attr('founders_map'), dict())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('specials_map'), dict())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('supporters_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('excluded_delegators_set'), set())

        self.assertEqual(100, cnf_prsr.get_conf_obj_attr('min_delegation_amt'))
        self.assertEqual(cnf_prsr.get_conf_obj_attr('prcnt_scale'), None)
        self.assertEqual(cnf_prsr.get_conf_obj_attr('pymnt_scale'), None)

    def test_validate_scales(self):
        data_fine = """
        version : 1.0
        baking_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        payment_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        founders_map : {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5}
        owners_map : {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj':0.5}
        service_fee : 4.5 
        pymnt_scale : 3
        prcnt_scale : 5
        """

        managers = {'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj',
                    'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj'}
        cnf_prsr = BakingYamlConfParser(data_fine, dict(), managers)
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(cnf_prsr.get_conf_obj_attr('baking_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_pkh'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_manager'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_type'), AddrType.TZ)
        self.assertEqual(0, cnf_prsr.get_conf_obj_attr('min_delegation_amt'))
        self.assertEqual(cnf_prsr.get_conf_obj_attr('excluded_delegators_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('prcnt_scale'), 5)
        self.assertEqual(cnf_prsr.get_conf_obj_attr('pymnt_scale'), 3)

    def test_validate_empty(self):
        data_fine = """
        version : 1.0
        baking_address : tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        payment_address : KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj
        service_fee : 4.5
        founders_map : {}
        owners_map : {}
        prcnt_scale : None
        pymnt_scale : None
        specials_map : {}
        supporters_set : {}
        min_delegation_amt : 0
        excluded_delegators_set : {}
        """

        managers = {'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj',
                    'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj'}
        cnf_prsr = BakingYamlConfParser(data_fine, dict(), managers)
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(cnf_prsr.get_conf_obj_attr('baking_address'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address'), 'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_pkh'), 'KT1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_manager'), 'tz1Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj')
        self.assertEqual(cnf_prsr.get_conf_obj_attr('payment_address_type'), AddrType.KT)
        self.assertEqual(0, cnf_prsr.get_conf_obj_attr('min_delegation_amt'))
        self.assertEqual(cnf_prsr.get_conf_obj_attr('excluded_delegators_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('supporters_set'), set())
        self.assertEqual(cnf_prsr.get_conf_obj_attr('prcnt_scale'), None)
        self.assertEqual(cnf_prsr.get_conf_obj_attr('pymnt_scale'), None)
