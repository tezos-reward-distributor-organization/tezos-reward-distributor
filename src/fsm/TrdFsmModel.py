from abc import ABC, abstractmethod


class TrdFsmModel(ABC):

    @abstractmethod
    def current(self):
        pass

    @abstractmethod
    def is_state(self, state):
        pass

    @abstractmethod
    def trigger_event(self, event, args_map=None):
        pass

    @abstractmethod
    def is_complete(self):
        pass
