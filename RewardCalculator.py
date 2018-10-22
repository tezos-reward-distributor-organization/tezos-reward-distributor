from abc import ABC, abstractmethod

class RewardCalculator(ABC):
    def __init__(self, founders_map):
        self.founders_map = founders_map
        self.total_rewards=0
        super().__init__()

    @abstractmethod
    def calculate(self):
        pass

    def get_total_rewards(self):
        return self.total_rewards

