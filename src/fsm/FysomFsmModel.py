from enum import Enum

from fysom import FysomGlobalMixin

from fsm.TrdFsmModel import TrdFsmModel


class FysomFsmModel(FysomGlobalMixin, TrdFsmModel):
    def __init__(self, gfsm) -> None:
        FysomGlobalMixin.GSM = gfsm
        self.state = None
        super(FysomFsmModel, self).__init__()

    def current(self):
        return self.state

    def is_state(self, state):
        return self.isstate(state)

    def can(self, event):
        return self.can(event)

    def trigger_event(self, event, args_map=None):
        if args_map is None: args_map = dict()
        if isinstance(event, Enum): event = event.name

        if args_map:
            self.trigger(event, **args_map)
        else:
            self.trigger(event)

    def is_complete(self):
        return self.is_finished()
