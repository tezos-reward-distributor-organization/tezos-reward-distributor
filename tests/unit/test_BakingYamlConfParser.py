import vcr
from unittest import TestCase
from unittest.mock import patch, MagicMock
from src.Constants import (
    PUBLIC_NODE_URL,
    PRIVATE_SIGNER_URL,
    DEFAULT_NETWORK_CONFIG_MAP,
)
from src.Constants import DryRun
from src.cli.client_manager import ClientManager
from src.config.addr_type import AddrType
from src.config.yaml_baking_conf_parser import BakingYamlConfParser
from src.rpc.rpc_block_api import RpcBlockApiImpl

node_endpoint = PUBLIC_NODE_URL["MAINNET"]
network = DEFAULT_NETWORK_CONFIG_MAP["MAINNET"]


@patch(
    "cli.client_manager.ClientManager.check_pkh_known_by_signer",
    MagicMock(return_value=True),
)
class TestYamlAppConfParser(TestCase):
    def setUp(self):
        self.mainnet_public_node_url = node_endpoint
        self.signer_endpoint = PRIVATE_SIGNER_URL

    @vcr.use_cassette(
        "tests/unit/cassettes/test_validate.yaml",
        filter_headers=["X-API-Key", "authorization"],
        decode_compressed_response=True,
    )
    def test_validate(self):
        data_fine = """
        version: 1.0
        baking_address: tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194
        payment_address: tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194
        founders_map: {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 0.5}
        owners_map: {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 0.5}
        supporters_set:
        service_fee: 4.53
        reactivate_zeroed: False
        delegator_pays_ra_fee: True
        plugins:
          enabled:
        """

        wallet_client_manager = ClientManager(
            self.mainnet_public_node_url, self.signer_endpoint
        )

        block_api = RpcBlockApiImpl(network, self.mainnet_public_node_url)
        cnf_prsr = BakingYamlConfParser(
            data_fine,
            wallet_client_manager,
            provider_factory=None,
            network_config=network,
            node_url=self.mainnet_public_node_url,
            block_api=block_api,
            dry_run=DryRun.NO_SIGNER,
        )
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("baking_address"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("payment_address"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )

        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("__payment_address_pkh"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("__payment_address_manager"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("__payment_address_type").value,
            AddrType.TZ.value,
        )

        self.assertEqual(cnf_prsr.get_conf_obj_attr("min_delegation_amt"), 0)
        self.assertEqual(cnf_prsr.get_conf_obj_attr("min_payment_amt"), 0)

        self.assertEqual(cnf_prsr.get_conf_obj_attr("reactivate_zeroed"), False)
        self.assertEqual(cnf_prsr.get_conf_obj_attr("delegator_pays_ra_fee"), True)

        self.assertTrue(cnf_prsr.get_conf_obj_attr("rewards_type").isActual())

        plugins = cnf_prsr.get_conf_obj_attr("plugins")
        self.assertIsInstance(plugins, dict)
        self.assertIsNone(plugins["enabled"], None)

    @vcr.use_cassette(
        "tests/unit/cassettes/test_validate_no_founders_map.yaml",
        filter_headers=["X-API-Key", "authorization"],
        decode_compressed_response=True,
    )
    def test_validate_no_founders_map(self):
        data_no_founders = """
        version: 1.0
        baking_address: tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194
        payment_address: tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194
        owners_map: {'KT2Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 0.5,'KT3Z1tMai15JWUWeN2PKL9faXXVPMuWamzJj': 0.5}
        supporters_set: None
        service_fee: 4.5
        reactivate_zeroed: False
        delegator_pays_ra_fee: True
        rewards_type:
        plugins:
          enabled:
        """

        wallet_client_manager = ClientManager(
            self.mainnet_public_node_url, self.signer_endpoint
        )

        block_api = RpcBlockApiImpl(network, self.mainnet_public_node_url)
        cnf_prsr = BakingYamlConfParser(
            data_no_founders,
            wallet_client_manager,
            provider_factory=None,
            network_config=network,
            node_url=self.mainnet_public_node_url,
            block_api=block_api,
            dry_run=DryRun.NO_SIGNER,
        )
        cnf_prsr.parse()
        cnf_prsr.validate()

        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("baking_address"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("payment_address"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("__payment_address_pkh"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("__payment_address_manager"),
            "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194",
        )
        self.assertEqual(
            cnf_prsr.get_conf_obj_attr("__payment_address_type").value,
            AddrType.TZ.value,
        )

        self.assertEqual(cnf_prsr.get_conf_obj_attr("founders_map"), dict())
        self.assertEqual(cnf_prsr.get_conf_obj_attr("specials_map"), dict())
        self.assertEqual(cnf_prsr.get_conf_obj_attr("supporters_set"), set())

        self.assertEqual(cnf_prsr.get_conf_obj_attr("min_delegation_amt"), 0)
        self.assertEqual(cnf_prsr.get_conf_obj_attr("min_payment_amt"), 0)

        self.assertEqual(cnf_prsr.get_conf_obj_attr("reactivate_zeroed"), False)
        self.assertEqual(cnf_prsr.get_conf_obj_attr("delegator_pays_ra_fee"), True)

        self.assertTrue(cnf_prsr.get_conf_obj_attr("rewards_type").isActual())

        plugins = cnf_prsr.get_conf_obj_attr("plugins")
        self.assertIsInstance(plugins, dict)
        self.assertIsNone(plugins["enabled"], None)

    def test_validate_plugins(self):
        data = """
        baking_address: tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194
        plugins:
          enabled:
          - plug1
          - plug2
        """

        block_api = RpcBlockApiImpl(network, self.mainnet_public_node_url)
        cnf_prsr = BakingYamlConfParser(
            data,
            clnt_mngr=None,
            provider_factory=None,
            network_config=None,
            node_url="",
            block_api=block_api,
        )
        cnf_prsr.parse()
        cnf_prsr.validate_plugins(cnf_prsr.get_conf_obj())

        plugins = cnf_prsr.get_conf_obj_attr("plugins")
        self.assertIsInstance(plugins, dict)
        self.assertIsInstance(plugins["enabled"], list)
        self.assertEqual(len(plugins["enabled"]), 2)
