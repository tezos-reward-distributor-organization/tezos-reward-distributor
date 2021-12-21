from NetworkConfiguration import default_network_config_map
from tzkt.tzkt_block_api import TzKTBlockApiImpl


def test_get_head():
    tzkt_impl = TzKTBlockApiImpl(nw=default_network_config_map["MAINNET"])
    (cycle, level) = tzkt_impl.get_current_cycle_and_level()
    assert cycle > 300
    assert level > 900000
