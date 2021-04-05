import pytest
from src.tzkt.tzkt_api import TzKTApi, TzKTApiError

def test_request_no_content_response():
    """Test the handling of API calls which respond with no content (204).
    Issue: 
    https://github.com/tezos-reward-distributor-organization/tezos-reward-distributor/issues/404
    """

    # The baker address exists **only** on the mainnet
    baker_address = "tz1NortRftucvAkD1J58L32EhSVrQEWJCEnB"
    base_url = "https://api.carthage.tzkt.io/v1/"
    timeout = 30
    cycle = 201
    tzkt = TzKTApi(base_url, timeout)
    request_path = f"rewards/split/{baker_address}/{cycle}"
    with pytest.raises(TzKTApiError, match="TzKT returned 204 error"):
        res = tzkt._request(request_path, offset=0, limit=10000)
    