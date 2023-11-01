import pytest
from src.blockwatch.tzpro_block_api import TzProBlockApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP
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
    return TzProBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


def test_get_revelation(address_api):
    assert address_api.get_revelation(MAINNET_ADDRESS_DELEGATOR)


class MockCycleLevelResponse(MockResponse):
    def json(self):
        return {"cycle": 523, "height": 2701515}


@patch(
    "src.blockwatch.tzpro_block_api.requests.get",
    MagicMock(return_value=MockCycleLevelResponse()),
)
def test_get_current_cycle_and_level(address_api):
    # NOTE: The block count for tzpro is incremented internally by one to sync tzpro with tzkt
    assert address_api.get_current_cycle_and_level() == (523, 2701515 + 1)


def test_get_delegatable_baker(address_api):
    assert address_api.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)


def test_get_delegatable_non_baker(address_api):
    assert not address_api.get_delegatable(MAINNET_ADDRESS_DELEGATOR)
