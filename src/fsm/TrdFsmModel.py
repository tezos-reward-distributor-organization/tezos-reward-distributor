class TrdFsmModel:
    def __init__(self, fsm) -> None:
        super().__init__()
        self.internal_fsm = fsm

    def current(self):
        return self.internal_fsm.current

    def is_state(self, state):
        return self.internal_fsm.isstate(state)

    def can(self, event):
        return self.internal_fsm.can(event)

    def trigger(self, event, args_map=None):
        if args_map is None: args_map = dict()
        self.internal_fsm.trigger(event, **args_map)

    def is_finished(self):
        return self.internal_fsm.is_finished()
