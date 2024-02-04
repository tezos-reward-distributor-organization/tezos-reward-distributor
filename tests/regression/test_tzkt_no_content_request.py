import pytest
import vcr
from http import HTTPStatus
from unittest.mock import patch, MagicMock
from src.tzkt.tzkt_api import TzKTApi, TzKTApiError
from src.Constants import TZKT_PUBLIC_API_URL


class NoContentResponse:
    status_code = HTTPStatus.NO_CONTENT
    text = ""


@patch("tzkt.tzkt_api.requests.get", MagicMock(return_value=NoContentResponse()))
def test_request_no_content_response():
    """Test the handling of API calls which respond with no content (204).
    Issue:
    https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/404
    """

    # The baker address exists **only** on the mainnet
    baker_address = "tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB"
    base_url = ""
    timeout = 30
    cycle = 201
    tzkt = TzKTApi(base_url, timeout)
    request_path = f"rewards/split/{baker_address}/{cycle}"
    res = tzkt._request(request_path, offset=0, limit=10000)
    assert res is None


def test_request_dns_lookup_error():
    """Test the handling of API calls which respond with a DNS lookup error."""

    # The baker address exists **only** on the mainnet
    baker_address = "tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB"
    base_url = "https://not_existent_domain_name.com"
    timeout = 30
    cycle = 201
    tzkt = TzKTApi(base_url, timeout)
    request_path = f"rewards/split/{baker_address}/{cycle}"
    with pytest.raises(TzKTApiError, match="DNS lookup failed"):
        _ = tzkt._request(request_path, offset=0, limit=10000)


@vcr.use_cassette(
    "tests/regression/cassettes/test_request_content_response.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_request_content_response():
    """Test the handling of API calls which respond with a content (200)."""
    baker_address = "tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB"
    base_url = TZKT_PUBLIC_API_URL["MAINNET"]
    timeout = 30
    cycle = 201
    tzkt = TzKTApi(base_url, timeout)
    request_path = f"rewards/split/{baker_address}/{cycle}"
    response = tzkt._request(request_path, offset=0, limit=10000)
    assert isinstance(response, dict)
    assert response["cycle"] == cycle
