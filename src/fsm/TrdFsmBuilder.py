from abc import abstractmethod, ABC


class TrdFsmBuilder(ABC):

    @abstractmethod
    def add_initial_state(self, name, on_leave=None):
        pass

    @abstractmethod
    def add_final_state(self, name, on_enter=None):
        pass

    @abstractmethod
    def add_state(self, state, initial=False, final=False, on_enter=None, on_leave=None, on_reenter=None):
        pass

    @abstractmethod
    def add_global_transition(self, event, dst, on_before=None, on_after=None):
        pass

    @abstractmethod
    def add_transition(self, event, src, dst, on_before=None, on_after=None, conditions=None, condition_target=True):
        pass

    @abstractmethod
    def add_conditional_transition(self, event, src, condition, pass_dst, not_pass_dst=None):
        pass

    @abstractmethod
    def build(self):
        pass
