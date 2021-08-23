from abc import ABC, abstractmethod

# TODO: we should check if we are on mainnet, or a testnet
# We could add a get_current_protocol() method and check against it
LAST_FLORENCE_LEVEL = 1589248


class BlockApi(ABC):
    def __init__(self, nw):
        super(BlockApi, self).__init__()
        self.nw = nw

    @abstractmethod
    def get_current_level(self):
        pass

    @abstractmethod
    def get_current_cycle(self):
        pass

    def level_in_cycle(self, level):
        if level > LAST_FLORENCE_LEVEL:
            # Since protocol Granada
            return ((level - LAST_FLORENCE_LEVEL) % self.nw['BLOCKS_PER_CYCLE']) - 1
        else:
            # Until protocol Florence
            return (level % self.nw['BLOCKS_PER_CYCLE']) - 1
