import pytest
from src.rpc.rpc_block_api import RpcBlockApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import PUBLIC_NODE_URL, DEFAULT_NETWORK_CONFIG_MAP

NORMAL_TEZOS_ADDRESS = "tz1N4UfQCahHkRShBanv9QP9TnmXNgCaqCyZ"
STAKENOW_ADDRESS = "tz1g8vkmcde6sWKaG2NN9WKzCkDM6Rziq194"


class MockResponse:
    def json(self):
        return None

    @property
    def status_code(self):
        return 200


@pytest.fixture
def address_api():
    return RpcBlockApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], PUBLIC_NODE_URL["MAINNET"]
    )


class MockRelevationResponse(MockResponse):
    def json(self):
        return "edpkuoocAEKZvkjJGRq4jUywMHUWo3CZH12tsdfDiHC3JE4Uyi1So3"


@patch(
    "src.rpc.rpc_block_api.requests.get",
    MagicMock(return_value=MockRelevationResponse()),
)
def test_get_revelation(address_api):
    assert address_api.get_revelation(NORMAL_TEZOS_ADDRESS)


class MockCycleLevelResponse(MockResponse):
    def json(self):
        return {"metadata": {"level_info": {"cycle": 434, "level": 1972459}}}


@patch(
    "src.rpc.rpc_block_api.requests.get",
    MagicMock(return_value=MockCycleLevelResponse()),
)
def test_get_current_cycle_and_level(address_api):
    assert address_api.get_current_cycle_and_level() == (434, 1972459)


class MockDelegatableResponse(MockResponse):
    def json(self):
        return {"delegated_contracts": [], "deactivated": False}


@patch(
    "src.rpc.rpc_block_api.requests.get",
    MagicMock(return_value=MockDelegatableResponse()),
)
def test_get_delegatable_baker(address_api):
    assert address_api.get_delegatable(STAKENOW_ADDRESS)


class MockNonDelegatableResponse(MockResponse):
    def json(self):
        return {}


@patch(
    "src.rpc.rpc_block_api.requests.get",
    MagicMock(return_value=MockNonDelegatableResponse()),
)
def test_get_delegatable_non_baker(address_api):
    assert not address_api.get_delegatable(NORMAL_TEZOS_ADDRESS)
