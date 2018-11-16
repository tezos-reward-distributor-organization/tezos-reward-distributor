from abc import ABC, abstractmethod

class RewardApi(ABC):
    def __init__(self):
        super().__init__()

    @abstractmethod
    def get_rewards_for_cycle_map(self, cycle):
        pass
