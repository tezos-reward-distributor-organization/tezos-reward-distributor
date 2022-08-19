import pytest
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP
from tzkt.tzkt_block_api import TzKTBlockApiImpl
from src.tzstats.tzstats_block_api import TzStatsBlockApiImpl
from tests.utils import Constants

NORMAL_TEZOS_ADDRESS = Constants.NORMAL_TEZOS_ADDRESS
STAKENOW_ADDRESS = Constants.STAKENOW_ADDRESS

# These tests should not be mocked but test the overall consistency
# accross all tezos APIs which are available in TRD


@pytest.fixture
def address_block_api_tzkt():
    return TzKTBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


@pytest.fixture
def address_block_api_tzstats():
    return TzStatsBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


def test_get_revelation(address_block_api_tzkt, address_block_api_tzstats):
    assert address_block_api_tzkt.get_revelation(
        NORMAL_TEZOS_ADDRESS
    ) == address_block_api_tzstats.get_revelation(NORMAL_TEZOS_ADDRESS)


def test_get_current_cycle_and_level(address_block_api_tzkt, address_block_api_tzstats):
    assert (
        address_block_api_tzkt.get_current_cycle_and_level()
        == address_block_api_tzstats.get_current_cycle_and_level()
    )
