from abc import ABC, abstractmethod


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
        level = self.get_current_level()
        if level > 1589248:
            # After Granada
            return ((level - 1589248) % self.nw['BLOCKS_PER_CYCLE']) - 1
        else:
            # Before Granada
            return (level % self.nw['BLOCKS_PER_CYCLE']) - 1
