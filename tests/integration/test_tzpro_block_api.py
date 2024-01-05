import os
import pytest
import vcr
from src.blockwatch.tzpro_block_api import TzProBlockApiImpl
from unittest.mock import patch, MagicMock
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP
from tests.utils import Constants

MAINNET_ADDRESS_DELEGATOR = Constants.MAINNET_ADDRESS_DELEGATOR
MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
TZPRO_API_KEY = os.environ.get("TZPRO_API_KEY")


@pytest.fixture
def address_api():
    return TzProBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], TZPRO_API_KEY)


@vcr.use_cassette(
    "tests/integration/cassettes/tzpro_api/test_get_revelation.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_revelation(address_api):
    assert address_api.get_revelation(MAINNET_ADDRESS_DELEGATOR)


@vcr.use_cassette(
    "tests/integration/cassettes/tzpro_api/test_get_current_cycle_and_level.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_current_cycle_and_level(address_api):
    # NOTE: The block count for tzpro is incremented internally by one to sync tzpro with tzkt
    assert address_api.get_current_cycle_and_level() == (690, 4873963)


@vcr.use_cassette(
    "tests/integration/cassettes/tzpro_api/test_get_delegatable_baker.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_delegatable_baker(address_api):
    assert address_api.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)


@vcr.use_cassette(
    "tests/integration/cassettes/tzpro_api/test_get_delegatable_non_baker.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_get_delegatable_non_baker(address_api):
    assert not address_api.get_delegatable(MAINNET_ADDRESS_DELEGATOR)
