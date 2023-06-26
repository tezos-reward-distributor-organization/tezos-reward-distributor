import pytest
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP
from tzkt.tzkt_block_api import TzKTBlockApiImpl
from tests.utils import Constants

MAINNET_ADDRESS_DELEGATOR = Constants.MAINNET_ADDRESS_DELEGATOR
MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER


class MockResponse:
    def json(self):
        return None

    @property
    def status_code(self):
        return 200


@pytest.fixture
def address_api():
    return TzKTBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


class MockRelevationResponse(MockResponse):
    def json(self):
        return {"revealed": True}


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=MockRelevationResponse()),
)
def test_get_revelation(address_api):
    assert address_api.get_revelation(MAINNET_ADDRESS_DELEGATOR)


class MockCycleLevelResponse(MockResponse):
    def json(self):
        return {"synced": True, "cycle": 434, "level": 1972459}


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=MockCycleLevelResponse()),
)
def test_get_current_cycle_and_level(address_api):
    assert address_api.get_current_cycle_and_level() == (434, 1972459)


class MockDelegatableResponse(MockResponse):
    def json(self):
        return {"type": "delegate", "active": True}


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=MockDelegatableResponse()),
)
def test_get_delegatable_baker(address_api):
    assert address_api.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)


class MockNonDelegatableResponse(MockResponse):
    def json(self):
        return {"type": "user", "active": True}


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=MockNonDelegatableResponse()),
)
def test_get_delegatable_non_baker(address_api):
    assert not address_api.get_delegatable(MAINNET_ADDRESS_DELEGATOR)
