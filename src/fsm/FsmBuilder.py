from enum import Enum

from fysom import Fysom, FysomGlobal

from fsm.TrdFsmModel import TrdFsmModel
from fsm.TrdGFsmModel import TrdGFsmModel

ALL_STATES = '*'
SAME_STATE = '='


class FsmBuilder:

    def __init__(self):
        self.states = []
        self.transitions = []
        self.callbacks = {}
        self.initial = None
        self.final = None

    def add_initial_state(self, name, on_leave=None):
        self.add_state(name, initial=True, on_leave=on_leave)

    def add_final_state(self, name, on_enter=None):
        self.add_state(name, final=True, on_enter=on_enter)

    def add_state(self, state, initial=False, final=False, on_enter=None, on_leave=None, on_reenter=None):
        if isinstance(state, Enum): state = state.name

        if initial: self.initial = state
        if final: self.final = state

        self.states.append(state)

        if on_enter: self.callbacks['on_enter_' + str(state)] = on_enter
        if on_leave: self.callbacks['on_leave_' + str(state)] = on_leave
        if on_reenter: self.callbacks['on_reenter_' + str(state)] = on_reenter

    def add_state_async_leave(self, name, on_enter=None):
        self.add_state(name, on_leave=lambda e: False, on_enter=on_enter)

    def add_global_transition(self, event, dst, on_before=None, on_after=None, cond=None):
        return self.add_transition(event, ALL_STATES, dst, on_before=on_before, on_after=on_after, conditions=cond)

    def add_transition(self, event, src, dst, on_before=None, on_after=None, conditions=None):
        if isinstance(event, Enum): event = event.name
        if not isinstance(src, list): src = [src]

        src = [e.name if isinstance(e, Enum) else e for e in src]
        if isinstance(dst, Enum): dst = dst.name

        for s in src:
            if s != ALL_STATES and s not in self.states:
                raise Exception("Unknown source state:" + str(s))

        if dst != SAME_STATE and dst not in self.states:
            raise Exception("Unknown destination state:" + str(dst))

        self.transitions.append({'name': event, 'src': src, 'dst': dst, 'cond': conditions})

        if on_before: self.callbacks['on_before_' + str(event)] = on_before
        if on_after: self.callbacks['on_after_' + str(event)] = on_after

    def build(self):
        fsm = TrdFsmModel(Fysom(initial=self.initial,
                                events=self.transitions,
                                callbacks=self.callbacks,
                                final=self.final))
        return fsm

    def build_blobal(self):
        fsm = TrdGFsmModel(FysomGlobal(initial=self.initial,
                                events=self.transitions,
                                callbacks=self.callbacks,
                                state_field='state',
                                final=self.final)
                                )
        return fsm
