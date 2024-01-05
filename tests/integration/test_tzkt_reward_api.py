import os
import vcr
import pytest
from unittest.mock import patch, MagicMock
from src.Constants import (
    RewardsType,
    DEFAULT_NETWORK_CONFIG_MAP,
    MAX_SEQUENT_CALLS,
)
from src.blockwatch.tzpro_reward_api import TzProRewardApiImpl
from src.tzkt.tzkt_reward_api import TzKTRewardApiImpl, RewardLog
from tests.utils import Constants

MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
CYCLE = 100

"""
These tests are cached. To re-run, delete contents of the tzkt_data folder.
"""

dummy_addr_dict = dict(
    pkh="pkh",
    originated=False,
    alias="alias",
    sk="secret_key",
    manager="manager",
    revealed=True,
)


@patch("src.tzkt.tzkt_reward_api.sleep", MagicMock())
@pytest.mark.parametrize(
    "address,cycle",
    [
        ("tz1NRGxXV9h6SdNaZLcgmjuLx3hyy2f8YoGN", 650),
        ("tz1MbhmEwEAzzfb3naSr7vTp4mDxB8HsknA9", 623),
        ("tz1S8e9GgdZG78XJRB3NqabfWeM37GnhZMWQ", 683),
        ("tz1RV1MBbZMR68tacosb7Mwj6LkbPSUS1er1", 644),
        ("tz1WnfXMPaNTBmH7DBPwqCWs9cPDJdkGBTZ8", 600),
    ],
)
def test_expected_rewards(address, cycle):
    cassette_path = f"tests/integration/cassettes/tzkt_api/test_expected_rewards_{address}_{cycle}.yaml"
    with vcr.use_cassette(
        cassette_path,
        filter_headers=["X-API-Key", "authorization"],
        decode_compressed_response=True,
    ):
        tzpro_impl = TzProRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
            baking_address=address,
            tzpro_api_key=os.environ.get("TZPRO_API_KEY"),
        )
        tzpro_rewards = tzpro_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        tzkt_impl = TzKTRewardApiImpl(
            nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], baking_address=address
        )
        tzkt_rewards = tzkt_impl.get_rewards_for_cycle_map(cycle, RewardsType.ACTUAL)

        assert (
            tzpro_rewards.delegate_staking_balance
            == tzkt_rewards.delegate_staking_balance
        )
        assert (
            tzpro_rewards.delegate_staking_balance
            == tzkt_rewards.delegate_staking_balance
        )
        assert tzpro_rewards.total_reward_amount == tzkt_rewards.total_reward_amount
        assert tzpro_rewards.num_baking_rights == tzkt_rewards.num_baking_rights

        for address, balances in tzpro_rewards.delegator_balance_dict.items():
            assert (
                address in tzkt_rewards.delegator_balance_dict
            ), f"{address} is missing"
            assert balances["staking_balance"] == pytest.approx(
                tzkt_rewards.delegator_balance_dict[address]["staking_balance"],
                1,
            ), address


@patch("src.tzkt.tzkt_reward_api.sleep", MagicMock())
@vcr.use_cassette(
    "tests/integration/cassettes/tzkt_api/test_update_current_balances.yaml",
    filter_headers=["X-API-Key", "authorization"],
    decode_compressed_response=True,
)
def test_update_current_balances():
    log_items = [
        RewardLog(
            address="KT1Np1h72jGkRkfxNHLXNNJLHNbj9doPz4bR",
            type="D",
            staking_balance=100500,
            current_balance=0,
        )
    ]
    tzkt_impl = TzKTRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address="tz1gk3TDbU7cJuiBRMhwQXVvgDnjsxuWhcEA",
    )
    tzkt_impl.update_current_balances(log_items)
    assert 0 != log_items[0].current_balance


@pytest.fixture
def address_api():
    return TzKTRewardApiImpl(
        nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"],
        baking_address=MAINNET_ADDRESS_STAKENOW_BAKER,
    )


class Mock_404_Response:
    def json(self):
        return None

    @property
    def status_code(self):
        return 404

    @property
    def text(self):
        return "404 Error happened"


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=Mock_404_Response()),
)
@patch("tzkt.tzkt_api.sleep", MagicMock())
@patch("tzkt.tzkt_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_tzkt_terminate_404(address_api):
    with pytest.raises(
        Exception,
        match="TzKT returned 404 error:\n404 Error happened",
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )


class Mock_500_Response:
    def json(self):
        return {}

    @property
    def status_code(self):
        return 500

    @property
    def text(self):
        return "500 BAD REQUEST"


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=Mock_500_Response()),
)
@patch("tzkt.tzkt_api.sleep", MagicMock())
@patch("tzkt.tzkt_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_tzkt_retry_500(address_api):
    with pytest.raises(
        Exception,
        match=r"Max sequent calls number exceeded \({}\)".format(MAX_SEQUENT_CALLS),
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )


class Mock_204_Response:
    def json(self):
        return {}

    @property
    def status_code(self):
        return 204

    @property
    def text(self):
        return "204 NO CONTENT"


@patch(
    "src.tzkt.tzkt_api.requests.get",
    MagicMock(return_value=Mock_204_Response()),
)
@patch("tzkt.tzkt_api.sleep", MagicMock())
@patch("tzkt.tzkt_api.logger", MagicMock(debug=MagicMock(side_effect=print)))
def test_tzkt_retry_204(address_api):
    with pytest.raises(
        Exception,
        match=r"Max sequent calls number exceeded \({}\)".format(MAX_SEQUENT_CALLS),
    ):
        _ = address_api.get_rewards_for_cycle_map(
            cycle=CYCLE, rewards_type=RewardsType.ACTUAL
        )
