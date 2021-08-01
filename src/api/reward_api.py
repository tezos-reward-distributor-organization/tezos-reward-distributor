from abc import ABC, abstractmethod


class RewardApi(ABC):
    def __init__(self):
        super().__init__()
        self.dexter_contracts_set = []

    @abstractmethod
    def get_rewards_for_cycle_map(self, cycle, rewards_type):
        pass

    def set_dexter_contracts_set(self, dexter_contracts_set):
        self.dexter_contracts_set = dexter_contracts_set
