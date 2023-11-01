import unittest
from config.yaml_baking_conf_parser import BakingYamlConfParser, ConfigurationException
from api.provider_factory import ProviderFactory
from tests.utils import make_config
from Constants import DryRun
from util.address_validator import AddressValidator
from model.baking_conf import BAKING_ADDRESS


class TestYamlBakingConfigParser(unittest.TestCase):
    baking_config = make_config(
        baking_address="tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
        payment_address="tz1gtHbmBF3TSebsgJfJPvUB2e9x8EDeNm6V",
        service_fee=10,
        min_delegation_amt=0,
        min_payment_amt=0,
    )
    factory = ProviderFactory(provider="prpc")

    def setUp(self):
        self.baking_conf_parser = BakingYamlConfParser(
            self.baking_config,
            None,
            None,
            None,
            None,
            block_api=self.factory,
            api_base_url=None,
            dry_run=DryRun.NO_SIGNER,
        )
        self.block_api = unittest.mock.MagicMock()
        self.address_validator = AddressValidator()
        self.baking_conf_parser.block_api = self.block_api
        self.baking_conf_parser.address_validator = self.address_validator

    def test_valid_address(self):
        conf_obj = {BAKING_ADDRESS: "tz1qwertyuiopasdfghjklzxcvbnm1234567"}
        self.block_api.get_revelation.return_value = True
        self.block_api.get_delegatable.return_value = True
        self.baking_conf_parser.validate_baking_address(conf_obj)

    def test_missing_address(self):
        conf_obj = {}
        with self.assertRaises(ConfigurationException) as exception:
            self.baking_conf_parser.validate_baking_address(conf_obj)
        self.assertEqual(str(exception.exception), "Baking address must be set")

    def test_invalid_address(self):
        conf_obj = {BAKING_ADDRESS: "INVALID_ADDRESS"}
        with self.assertRaises(ConfigurationException) as exception:
            self.baking_conf_parser.validate_baking_address(conf_obj)
        self.assertEqual(
            str(exception.exception),
            "Baking address must be a valid tz address of length 36",
        )
