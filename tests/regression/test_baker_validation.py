import pytest
from cli.client_manager import ClientManager
from config.yaml_baking_conf_parser import BakingYamlConfParser
from exception.configuration import ConfigurationException
from Constants import PUBLIC_NODE_URL, PRIVATE_SIGNER_URL, DryRun
from rpc.rpc_block_api import RpcBlockApiImpl
from tzkt.tzkt_block_api import TzKTBlockApiImpl
from tzstats.tzstats_block_api import TzStatsBlockApiImpl
from tests.utils import Constants


node_endpoint = PUBLIC_NODE_URL["MAINNET"]
network = {"NAME": "MAINNET"}


@pytest.mark.parametrize(
    "block_api",
    [
        pytest.param(RpcBlockApiImpl(network, node_endpoint), id="RpcBlockApiImpl"),
        pytest.param(TzKTBlockApiImpl(network), id="TzKTBlockApiImpl"),
        pytest.param(TzStatsBlockApiImpl(network), id="TzStatsBlockApiImpl"),
    ],
)
def test_address_is_baker_address(block_api):
    data_fine = """
    version: 1.0
    baking_address: {0}
    """.format(
        Constants.STAKENOW_ADDRESS
    )

    wallet_client_manager = ClientManager(node_endpoint, PRIVATE_SIGNER_URL)
    cnf_prsr = BakingYamlConfParser(
        data_fine,
        wallet_client_manager,
        provider_factory=None,
        network_config=network,
        node_url=node_endpoint,
        block_api=block_api,
        dry_run=DryRun.NO_SIGNER,
    )
    cnf_prsr.parse()
    assert cnf_prsr.validate_baking_address(cnf_prsr.conf_obj) is None


@pytest.mark.parametrize(
    "block_api",
    [
        pytest.param(RpcBlockApiImpl(network, node_endpoint), id="RpcBlockApiImpl"),
        pytest.param(TzKTBlockApiImpl(network), id="TzKTBlockApiImpl"),
        pytest.param(TzStatsBlockApiImpl(network), id="TzStatsBlockApiImpl"),
    ],
)
def test_address_is_not_baker_address(block_api):
    data_fine = """
    version: 1.0
    baking_address: tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ
    """

    wallet_client_manager = ClientManager(node_endpoint, PRIVATE_SIGNER_URL)
    cnf_prsr = BakingYamlConfParser(
        data_fine,
        wallet_client_manager,
        provider_factory=None,
        network_config=network,
        node_url=node_endpoint,
        block_api=block_api,
        dry_run=DryRun.NO_SIGNER,
    )
    cnf_prsr.parse()
    with pytest.raises(
        ConfigurationException,
        match="Baking address tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ is not enabled for delegation",
    ):
        cnf_prsr.validate_baking_address(cnf_prsr.conf_obj)


@pytest.mark.parametrize(
    "block_api",
    [
        pytest.param(RpcBlockApiImpl(network, node_endpoint), id="RpcBlockApiImpl"),
        pytest.param(TzKTBlockApiImpl(network), id="TzKTBlockApiImpl"),
        pytest.param(TzStatsBlockApiImpl(network), id="TzStatsBlockApiImpl"),
    ],
)
def test_invalid_baking_address(block_api):
    data_fine = """
    version: 1.0
    baking_address: tz123
    """

    wallet_client_manager = ClientManager(node_endpoint, PRIVATE_SIGNER_URL)
    cnf_prsr = BakingYamlConfParser(
        data_fine,
        wallet_client_manager,
        provider_factory=None,
        network_config=network,
        node_url=node_endpoint,
        block_api=block_api,
        dry_run=DryRun.NO_SIGNER,
    )
    cnf_prsr.parse()
    with pytest.raises(
        ConfigurationException,
        match="Baking address must be a valid tz address of length 36",
    ):
        cnf_prsr.validate_baking_address(cnf_prsr.conf_obj)
