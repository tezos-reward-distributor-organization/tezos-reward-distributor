ALL_STATES = '*'


class FsmBuilder:

    def __init__(self):
        self.states = []
        self.transitions = []
        self.callbacks = {}
        self.initial = None
        self.final = None

    def add_initial_state(self, name, on_leave=None):
        return self.add_state(name, initial=True, on_leave=on_leave)

    def add_final_state(self, name, on_enter=None):
        return self.add_state(name, final=True, on_enter=on_enter)

    def add_state(self, name, initial=False, final=False, on_enter=None, on_leave=None, on_reenter=None):
        if initial: self.initial = name
        if final: self.final = name

        self.states.append(name)

        if on_enter: self.callbacks['on_enter_' + name] = on_enter
        if on_leave: self.callbacks['en_leave_' + name] = on_leave
        if on_reenter: self.callbacks['en_reenter_' + name] = on_reenter

    def add_state_async_leave(self, name, on_enter=None):
        self.add_state(name, on_leave=lambda e: False, on_enter=on_enter)

    def add_global_transition(self, event, dst, on_before=None, on_after=None, cond=None):
        return self.add_transition(event, ALL_STATES, dst, on_before=on_before, on_after=on_after, conditions=cond)

    def add_transition(self, event, src, dst, on_before=None, on_after=None, conditions=None):

        if src != ALL_STATES and src not in self.states:
            raise Exception("Unknown source state!")

        if dst not in self.states:
            raise Exception("Unknown destination state!")

        self.transitions.append({'name': event, 'src': src, 'dst': dst, 'cond': conditions})

        if on_before: self.callbacks['on_before_' + event] = on_before
        if on_after: self.callbacks['on_after_' + event] = on_after
