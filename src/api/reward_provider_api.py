from abc import ABC, abstractmethod


class RewardProviderApi(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def provide_for_cycle(self, cycle, verbose=False):
        pass
