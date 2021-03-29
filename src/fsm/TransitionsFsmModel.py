from enum import Enum

from fsm.TrdFsmModel import TrdFsmModel


class TransitionsFsmModel(TrdFsmModel):
    def __init__(self, final_state) -> None:
        self.final_state = final_state.name if isinstance(final_state, Enum) else final_state
        self.machine = None
        self.state = None
        super(TransitionsFsmModel, self).__init__()

    def init(self, machine):
        self.machine = machine

    def current(self):
        return self.state

    def is_state(self, state):
        state = state.name if isinstance(state, Enum) else state
        return self.state == state

    def trigger_event(self, event, *args, **kwargs):
        if isinstance(event, Enum):
            event = event.name

        self.trigger(event, *args, **kwargs)

    def is_complete(self):
        return self.state == self.final_state
