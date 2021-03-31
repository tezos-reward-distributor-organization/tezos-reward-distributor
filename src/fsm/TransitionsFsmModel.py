from fsm.TrdFsmModel import TrdFsmModel
from fsm.fsm_helper import to_name


class TransitionsFsmModel(TrdFsmModel):
    def __init__(self, final_state) -> None:
        self.__final_state = to_name(final_state)
        self.__machine = None
        self.__state = None
        super(TransitionsFsmModel, self).__init__()

    def init(self, machine):
        self.__machine = machine

    @property
    def current(self):
        return self.__state

    def is_state(self, state):
        state = to_name(state)
        return self.__state == state

    def trigger_event(self, event, *args, **kwargs):
        event = to_name(event)

        self.trigger(event, *args, **kwargs)

    @property
    def is_complete(self):
        return self.__state == self.__final_state
