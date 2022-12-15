import pytest
from src.tzstats.tzstats_block_api import TzStatsBlockApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP
from tests.utils import Constants

NORMAL_TEZOS_ADDRESS = Constants.NORMAL_TEZOS_ADDRESS
STAKENOW_ADDRESS = Constants.STAKENOW_ADDRESS


class MockResponse:
    def json(self):
        return None

    @property
    def status_code(self):
        return 200


@pytest.fixture
def address_api():
    return TzStatsBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


def test_get_revelation(address_api):
    assert address_api.get_revelation(NORMAL_TEZOS_ADDRESS)


class MockCycleLevelResponse(MockResponse):
    def json(self):
        return {"cycle": 523, "height": 2701515}


@patch(
    "src.tzstats.tzstats_block_api.requests.get",
    MagicMock(return_value=MockCycleLevelResponse()),
)
def test_get_current_cycle_and_level(address_api):
    # NOTE: The block count for tzstats is incremented internally by one to synch tzstats with tzkt
    assert address_api.get_current_cycle_and_level() == (523, 2701515 + 1)


def test_get_delegatable_baker(address_api):
    assert address_api.get_delegatable(STAKENOW_ADDRESS)


def test_get_delegatable_non_baker(address_api):
    assert not address_api.get_delegatable(NORMAL_TEZOS_ADDRESS)
