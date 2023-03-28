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

MAINNET_ADDRESS_DELEGATOR = Constants.MAINNET_ADDRESS_DELEGATOR
MAINNET_ADDRESS_STAKENOW_BAKER = Constants.MAINNET_ADDRESS_STAKENOW_BAKER
MAINNET_ADDRESS_BAKEXTZ4ME_BAKER = Constants.MAINNET_ADDRESS_BAKEXTZ4ME_BAKER
GHOSTNET_ADDRESS_STAKENOW_BAKER = Constants.GHOSTNET_ADDRESS_STAKENOW_BAKER


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
        MAINNET_ADDRESS_DELEGATOR
    ) == address_block_api_tzstats.get_revelation(MAINNET_ADDRESS_DELEGATOR)
    assert address_block_api_tzkt.get_revelation(
        MAINNET_ADDRESS_DELEGATOR
    ) == address_block_api_rpc.get_revelation(MAINNET_ADDRESS_DELEGATOR)
    assert address_block_api_tzstats.get_revelation(
        MAINNET_ADDRESS_DELEGATOR
    ) == address_block_api_rpc.get_revelation(MAINNET_ADDRESS_DELEGATOR)


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
        MAINNET_ADDRESS_STAKENOW_BAKER
    ) == address_block_api_tzstats.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)
    assert address_block_api_tzkt.get_delegatable(
        MAINNET_ADDRESS_STAKENOW_BAKER
    ) == address_block_api_rpc.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)
    assert address_block_api_tzstats.get_delegatable(
        MAINNET_ADDRESS_STAKENOW_BAKER
    ) == address_block_api_rpc.get_delegatable(MAINNET_ADDRESS_STAKENOW_BAKER)


# NOTE: We are using a testnet balker where we can manage the amount of delegates
@pytest.fixture
def address_reward_api_tzkt():
    return TzKTRewardApiImpl(DEFAULT_NETWORK_CONFIG_MAP["GHOSTNET"], GHOSTNET_ADDRESS_STAKENOW_BAKER)


@pytest.fixture
def address_reward_api_tzstats():
    return TzStatsRewardApiImpl(DEFAULT_NETWORK_CONFIG_MAP["GHOSTNET"], GHOSTNET_ADDRESS_STAKENOW_BAKER)


@pytest.fixture
def address_reward_api_rpc():
    return RpcRewardApiImpl(
        DEFAULT_NETWORK_CONFIG_MAP["GHOSTNET"],
        GHOSTNET_ADDRESS_STAKENOW_BAKER,
        PUBLIC_NODE_URL["GHOSTNET"],
    )


def test_get_rewards_for_cycle_map(
    address_reward_api_tzkt,
    address_reward_api_tzstats,
    address_reward_api_rpc,
    current_cycle,
):
    last_cycle = current_cycle - 1
    rewards_tzkt = address_reward_api_tzkt.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )
    rewards_tzstats = address_reward_api_tzstats.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )
    rewards_rpc = address_reward_api_rpc.get_rewards_for_cycle_map(
        cycle=last_cycle, rewards_type=RewardsType.ACTUAL
    )

    # Check total_reward_amount
    assert rewards_tzkt.total_reward_amount == rewards_tzstats.total_reward_amount
    assert rewards_rpc.total_reward_amount == rewards_tzstats.total_reward_amount
    assert rewards_rpc.total_reward_amount == rewards_tzkt.total_reward_amount

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
        assert tzkt_balance_dict["current_balance"] == pytest.approx(
            rewards_rpc.delegator_balance_dict[tzkt_delegator_adress][
                "current_balance"
            ],
            1,
        )
        assert tzkt_balance_dict["staking_balance"] == pytest.approx(
            rewards_rpc.delegator_balance_dict[tzkt_delegator_adress][
                "staking_balance"
            ],
            1,
        )

        assert tzkt_balance_dict["current_balance"] == pytest.approx(
            rewards_tzstats.delegator_balance_dict[tzkt_delegator_adress][
                "current_balance"
            ],
            1,
        )
        assert tzkt_balance_dict["staking_balance"] == pytest.approx(
            rewards_tzstats.delegator_balance_dict[tzkt_delegator_adress][
                "staking_balance"
            ],
            1,
        )

    # Check num_baking_rights
    assert rewards_tzkt.num_baking_rights == rewards_tzstats.num_baking_rights
    assert rewards_rpc.num_baking_rights == rewards_tzstats.num_baking_rights
    assert rewards_rpc.num_baking_rights == rewards_tzkt.num_baking_rights

    # Check denunciation_rewards
    assert rewards_tzkt.denunciation_rewards == rewards_tzstats.denunciation_rewards
    assert rewards_rpc.denunciation_rewards == rewards_tzstats.denunciation_rewards
    assert rewards_rpc.denunciation_rewards == rewards_tzkt.denunciation_rewards

    # Check equivocation_losses
    assert rewards_tzkt.equivocation_losses == rewards_tzstats.equivocation_losses
    assert rewards_rpc.equivocation_losses == rewards_tzstats.equivocation_losses
    assert rewards_rpc.equivocation_losses == rewards_tzkt.equivocation_losses

    # Check offline_losses
    assert rewards_tzkt.offline_losses == rewards_tzstats.offline_losses
    assert rewards_rpc.offline_losses == rewards_tzstats.offline_losses
    assert rewards_rpc.offline_losses == rewards_tzkt.offline_losses

    # Check potential_endorsement_rewards
    # TODO: tzstats total_active_stake does not match rpc and tzkt exactly thus the approximation
    assert rewards_tzkt.potential_endorsement_rewards == pytest.approx(
        rewards_tzstats.potential_endorsement_rewards, 60000
    )
    assert rewards_rpc.potential_endorsement_rewards == pytest.approx(
        rewards_tzstats.potential_endorsement_rewards, 60000
    )
    assert (
        rewards_rpc.potential_endorsement_rewards
        == rewards_tzkt.potential_endorsement_rewards
    )

    # Check rewards_and_fees
    assert rewards_tzkt.rewards_and_fees == rewards_tzstats.rewards_and_fees
    assert rewards_rpc.rewards_and_fees == rewards_tzstats.rewards_and_fees
    assert rewards_rpc.rewards_and_fees == rewards_tzkt.rewards_and_fees

    # Check computed_reward_amount
    assert rewards_tzkt.computed_reward_amount == rewards_tzstats.computed_reward_amount
    assert rewards_rpc.computed_reward_amount == rewards_tzstats.computed_reward_amount
    assert rewards_rpc.computed_reward_amount == rewards_tzkt.computed_reward_amount
