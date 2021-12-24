from Constants import DEFAULT_NETWORK_CONFIG_MAP
from tzkt.tzkt_block_api import TzKTBlockApiImpl


def test_get_head():
    tzkt_impl = TzKTBlockApiImpl(nw=DEFAULT_NETWORK_CONFIG_MAP["MAINNET"])
    (cycle, level) = tzkt_impl.get_current_cycle_and_level()
    assert cycle > 300
    assert level > 900000
