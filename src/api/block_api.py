from abc import ABC, abstractmethod
from Constants import FIRST_GRANADA_LEVEL, FIRST_MUMBAI_LEVEL

# TODO: we should check if we are on mainnet, or a testnet
# we could add a get_current_protocol() method and check against it


class BlockApi(ABC):
    def __init__(self, nw):
        super(BlockApi, self).__init__()
        self.nw = nw

    @abstractmethod
    def get_current_cycle_and_level(self):
        pass

    def level_in_cycle(self, level):
        if level >= FIRST_MUMBAI_LEVEL:
            # Since protocol Mumbai
            return (level - FIRST_MUMBAI_LEVEL) % self.nw["BLOCKS_PER_CYCLE"]
        elif level >= FIRST_GRANADA_LEVEL:
            # Since protocol Granada
            return (level - FIRST_GRANADA_LEVEL) % self.nw["BLOCKS_PER_CYCLE"]
        else:
            # Until protocol Florence
            return (level % self.nw["BLOCKS_PER_CYCLE"]) - 1
