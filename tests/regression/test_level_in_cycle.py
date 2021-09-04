import pytest
from Constants import DEFAULT_NETWORK_CONFIG_MAP
from api.block_api import BlockApi

class DummyApiImpl(BlockApi):
    def __init__(self):
        super(DummyApiImpl, self).__init__(DEFAULT_NETWORK_CONFIG_MAP['MAINNET'])
    def get_current_cycle_and_level(self):
        return 0

def test_levels_in_cycle():

    # This test only works for blocks after granada because the network config
    # map is based on current mainnet values

    level_positions = [
        [ 1589249, 0],       # Granada activation level
        [ 1665240, 2263 ],
	]

    block = DummyApiImpl()

    for l in level_positions:
        assert block.level_in_cycle(l[0]) == l[1]
