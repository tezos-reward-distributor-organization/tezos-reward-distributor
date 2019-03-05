from abc import ABC, abstractmethod


class RewardCalculatorApi(ABC):

    # return rewards    : tuple (list of PaymentRecord objects, total rewards)
    @abstractmethod
    def calculate(self,cycle, verbose):
        pass
