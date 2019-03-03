from abc import ABC, abstractmethod

import itertools


class CalculatePhaseBase(ABC):

    @abstractmethod
    def calculate(self, input_list, total_amount):
        pass

    @staticmethod
    def filterskipped(reward_data):
        return itertools.filterfalse(lambda pr: pr.skipped, reward_data)

    @staticmethod
    def iterateskipped(reward_data):
        return itertools.filterfalse(lambda pr: not pr.skipped, reward_data)
