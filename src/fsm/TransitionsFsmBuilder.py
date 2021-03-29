import sys
from enum import Enum

from transitions import Machine

from fsm.TransitionsFsmModel import TransitionsFsmModel
from fsm.TrdFsmBuilder import TrdFsmBuilder

ALL_STATES = '*'
SAME_STATE = '='


class TransitionsFsmBuilder(TrdFsmBuilder):

    def __init__(self):
        self.states = []
        self.state_names = []
        self.transitions = []
        self.callbacks = {}
        self.initial = None
        self.final = None

    def add_initial_state(self, name, on_leave=None):
        self.add_state(name, initial=True, on_leave=on_leave)

    def add_final_state(self, name, on_enter=None):
        self.add_state(name, final=True, on_enter=on_enter)

    def add_state(self, state, initial=False, final=False, on_enter=None, on_leave=None, on_reenter=None):
        if isinstance(state, Enum):
            state = state.name

        if initial:
            self.initial = state
        if final:
            self.final = state

        state_dict = {'name': state}

        if on_enter:
            state_dict['on_enter'] = [on_enter]
        if on_leave:
            state_dict['on_exit'] = [on_leave]
        if on_reenter:
            print("reenter not supported!", file=sys.stderr)

        self.states.append(state_dict)
        self.state_names.append(state)
        pass

    def add_global_transition(self, event, dst, on_before=None, on_after=None):
        return self.add_transition(event, self.state_names, dst, on_before=on_before, on_after=on_after)

    def add_transition(self, event, src, dst, on_before=None, on_after=None, conditions=None, condition_target=True):
        if isinstance(event, Enum):
            event = event.name
        if not isinstance(src, list):
            src = [src]

        src = [e.name if isinstance(e, Enum) else e for e in src]
        if isinstance(dst, Enum): dst = dst.name

        for s in src:
            if s != ALL_STATES and s not in self.state_names:
                raise Exception("Unknown source state:" + str(s))

        if dst != SAME_STATE and dst not in self.state_names:
            raise Exception("Unknown destination state:" + str(dst))

        trigger_dict = {'trigger': event, 'source': src, 'dest': dst}

        if conditions:
            if condition_target:
                trigger_dict['conditions'] = conditions
            else:
                trigger_dict['unless'] = conditions

        if on_before:
            trigger_dict['before'] = on_before
        if on_after:
            trigger_dict['after'] = on_after

        self.transitions.append(trigger_dict)
        pass

    def add_conditional_transition(self, event, src, condition, pass_dst, not_pass_dst=None):

        self.add_transition(event, src, pass_dst, conditions=[condition])

        if not_pass_dst:
            self.add_transition(event, src, not_pass_dst, conditions=[condition], condition_target=False)

        pass

    def build(self):
        fsm = TransitionsFsmModel(self.final)
        machine = Machine(model=fsm, states=self.states, initial=self.initial, transitions=self.transitions, send_event=True)
        fsm.init(machine)

        return fsm
