class TrdFsmModel:
    def __init__(self, fsm) -> None:
        super().__init__()
        self.fsm = fsm

    def current(self):
        return self.fsm.current

    def is_state(self, state):
        return self.fsm.isstate(state)

    def can(self, event):
        return self.fsm.can(event)

    def trigger(self, event, args_map=None):
        if args_map is None: args_map = dict()
        self.fsm.trigger(event, **args_map)

    def is_finished(self):
        return self.fsm.is_finished()
