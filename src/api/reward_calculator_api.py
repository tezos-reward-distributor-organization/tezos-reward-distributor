from abc import ABC, abstractmethod


class RewardCalculatorApi(ABC):
    def __init__(self, founders_map):
        super(RewardCalculatorApi, self).__init__()

        self.founders_map = founders_map
        self.total_rewards = 0

    # return rewards    : tuple (list of PaymentRecord objects, total rewards)
    @abstractmethod
    def calculate(self):
        pass
