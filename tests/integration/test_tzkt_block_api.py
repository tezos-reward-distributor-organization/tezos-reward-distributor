from NetworkConfiguration import default_network_config_map
from tzkt.tzkt_block_api import TzKTBlockApiImpl


def test_get_head():
    tzkt_impl = TzKTBlockApiImpl(nw=default_network_config_map['MAINNET'])
    level = tzkt_impl.get_current_level()
    assert level > 900000
