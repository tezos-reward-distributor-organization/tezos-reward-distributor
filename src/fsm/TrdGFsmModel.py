from enum import Enum

from fysom import FysomGlobalMixin


class TrdGFsmModel(FysomGlobalMixin):
    def __init__(self, gfsm) -> None:
        FysomGlobalMixin.GSM = gfsm
        self.state = None
        super(TrdGFsmModel, self).__init__()

    def current(self):
        return self.current

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
