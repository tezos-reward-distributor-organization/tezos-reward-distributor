import pytest
import requests
from src.Constants import DEFAULT_NETWORK_CONFIG_MAP, PUBLIC_NODE_URL, RewardsType
from tests.utils import Constants

# Block APIs
from src.tzkt.tzkt_block_api import TzKTBlockApiImpl
from src.tzstats.tzstats_block_api import TzStatsBlockApiImpl
from src.rpc.rpc_block_api import RpcBlockApiImpl

# Reward APIs
from src.tzkt.tzkt_reward_api import TzKTRewardApiImpl
from src.tzstats.tzstats_reward_api import TzStatsRewardApiImpl
from src.rpc.rpc_reward_api import RpcRewardApiImpl

NORMAL_TEZOS_ADDRESS = Constants.NORMAL_TEZOS_ADDRESS
STAKENOW_ADDRESS = Constants.STAKENOW_ADDRESS
BAKEXTZ4ME_ADDRESS = Constants.BAKEXTZ4ME_ADDRESS
BAKEXTZ4ME_PAYOUT_ADDRESS = Constants.BAKEXTZ4ME_PAYOUT_ADDRESS

# These tests should not be mocked but test the overall consistency
# accross all tezos APIs which are available in TRD


@pytest.fixture
def address_block_api_tzkt():
    return TzKTBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


@pytest.fixture
def address_block_api_tzstats():
    return TzStatsBlockApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])


@pytest.fixture
def address_block_api_rpc():
    return RpcBlockApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], PUBLIC_NODE_URL["MAINNET"]
    )


@pytest.fixture
def current_cycle():
    tip = "https://api.tzstats.com/explorer/tip"
    resp = requests.get(tip, timeout=5)
    return int(resp.json()["cycle"])


def test_get_revelation(
    address_block_api_tzkt, address_block_api_tzstats, address_block_api_rpc
):
    assert address_block_api_tzkt.get_revelation(
        NORMAL_TEZOS_ADDRESS
    ) == address_block_api_tzstats.get_revelation(NORMAL_TEZOS_ADDRESS)
    assert address_block_api_tzkt.get_revelation(
        NORMAL_TEZOS_ADDRESS
    ) == address_block_api_rpc.get_revelation(NORMAL_TEZOS_ADDRESS)
    assert address_block_api_tzstats.get_revelation(
        NORMAL_TEZOS_ADDRESS
    ) == address_block_api_rpc.get_revelation(NORMAL_TEZOS_ADDRESS)


def test_get_current_cycle_and_level(
    address_block_api_tzkt, address_block_api_tzstats, address_block_api_rpc
):
    cycle_tzkt, level_tzkt = address_block_api_tzkt.get_current_cycle_and_level()
    (
        cycle_tzstats,
        level_tzstats,
    ) = address_block_api_tzstats.get_current_cycle_and_level()
    cycle_rpc, level_rpc = address_block_api_rpc.get_current_cycle_and_level()

    assert cycle_tzkt == cycle_tzstats
    assert cycle_rpc == cycle_tzstats
    assert cycle_tzkt == cycle_rpc

    # Allow a delta of 1 for level query
    assert abs(level_tzkt - level_tzstats) <= 1
    assert abs(level_rpc - level_tzstats) <= 1
    assert abs(level_tzkt - level_rpc) <= 1


def test_get_delegatable(
    address_block_api_tzkt, address_block_api_tzstats, address_block_api_rpc
):
    assert address_block_api_tzkt.get_delegatable(
        STAKENOW_ADDRESS
    ) == address_block_api_tzstats.get_delegatable(STAKENOW_ADDRESS)
    assert address_block_api_tzkt.get_delegatable(
        STAKENOW_ADDRESS
    ) == address_block_api_rpc.get_delegatable(STAKENOW_ADDRESS)
    assert address_block_api_tzstats.get_delegatable(
        STAKENOW_ADDRESS
    ) == address_block_api_rpc.get_delegatable(STAKENOW_ADDRESS)


# NOTE: We are using BAKEXTZ4ME since this baker has a managable amount of delegates
@pytest.fixture
def address_reward_api_tzkt():
    return TzKTRewardApiImpl(DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], BAKEXTZ4ME_ADDRESS)


@pytest.fixture
def address_reward_api_tzstats():
    return TzStatsRewardApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["MAINNET"], BAKEXTZ4ME_ADDRESS
    )


def test_get_rewards_for_cycle_map(
    address_reward_api_tzkt,
    address_reward_api_tzstats,
    current_cycle,
):
    last_cycle = current_cycle - 1
    rewards_tzkt = address_reward_api_tzkt.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )
    rewards_tzstats = address_reward_api_tzstats.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )

    # Check total_reward_amount
    assert rewards_tzkt.total_reward_amount == rewards_tzstats.total_reward_amount

    # Check delegate_staking_balance
    assert (
        rewards_tzkt.delegate_staking_balance
        == rewards_tzstats.delegate_staking_balance
    )
    # assert rewards_rpc.delegate_staking_balance == rewards_tzstats.delegate_staking_balance
    # assert rewards_rpc.delegate_staking_balance == rewards_tzkt.delegate_staking_balance

    # Check delegator_balance_dict
    for (
        tzkt_delegator_adress,
        tzkt_balance_dict,
    ) in rewards_tzkt.delegator_balance_dict.items():
        if BAKEXTZ4ME_PAYOUT_ADDRESS == tzkt_delegator_adress:
            continue

        tzstats_balance = rewards_tzstats.delegator_balance_dict.get(
            tzkt_delegator_adress,
        )
        if tzstats_balance is not None:
            assert tzkt_balance_dict["current_balance"] == pytest.approx(
                tzstats_balance["current_balance"],
                1,
            )
            assert tzkt_balance_dict["staking_balance"] == pytest.approx(
                tzstats_balance["staking_balance"],
                1,
            )

    # Check num_baking_rights
    assert rewards_tzkt.num_baking_rights == rewards_tzstats.num_baking_rights

    # Check denunciation_rewards
    assert rewards_tzkt.denunciation_rewards == rewards_tzstats.denunciation_rewards

    # Check equivocation_losses
    assert rewards_tzkt.equivocation_losses == rewards_tzstats.equivocation_losses

    # Check offline_losses
    assert rewards_tzkt.offline_losses == rewards_tzstats.offline_losses

    # Check potential_endorsement_rewards
    # TODO: tzstats total_active_stake does not match rpc and tzkt exactly thus the approximation
    assert rewards_tzkt.potential_endorsement_rewards == pytest.approx(
        rewards_tzstats.potential_endorsement_rewards, 60000
    )

    # Check rewards_and_fees
    assert rewards_tzkt.rewards_and_fees == rewards_tzstats.rewards_and_fees

    # Check computed_reward_amount
    assert rewards_tzkt.computed_reward_amount == rewards_tzstats.computed_reward_amount
