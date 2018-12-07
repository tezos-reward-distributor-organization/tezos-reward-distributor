from abc import ABC, abstractmethod
from math import floor


class BlockApi(ABC):
    def __init__(self, nw):
        super(BlockApi, self).__init__()
        self.nw = nw

    @abstractmethod
    def get_current_level(self, verbose=False):
        pass

    def level_to_cycle(self, level):
        return floor(level / self.nw['BLOCKS_PER_CYCLE'])

    def get_current_cycle(self):
        return self.level_to_cycle(self.get_current_level())
