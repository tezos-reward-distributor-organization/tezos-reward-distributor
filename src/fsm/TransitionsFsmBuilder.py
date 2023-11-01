from transitions import Machine

from fsm.TransitionsFsmModel import TransitionsFsmModel
from fsm.TrdFsmBuilder import TrdFsmBuilder
from fsm.fsm_helper import to_name, to_list

ALL_STATES = "*"
SAME_STATE = "="


class TransitionsFsmBuilder(TrdFsmBuilder):
    def __init__(self):
        self.__states = []
        self.__state_names = set()
        self.__transitions = []
        self.__callbacks = {}
        self.__initial = None
        self.__final = None
        self.__transition_complete_callback = None

    def add_transition_complete_callback(self, transition_complete_callback):
        self.__transition_complete_callback = transition_complete_callback

    def add_initial_state(self, name, on_leave=None):
        self.add_state(name, initial=True, on_leave=on_leave)

    def add_final_state(self, name, on_enter=None):
        self.add_state(name, final=True, on_enter=on_enter)

    def add_state(
        self, state, initial=False, final=False, on_enter=None, on_leave=None
    ):
        state = to_name(state)

        if initial:
            self.__initial = state
        if final:
            self.__final = state

        state_dict = {"name": state}

        if on_enter:
            state_dict["on_enter"] = [on_enter]
        if on_leave:
            state_dict["on_exit"] = [on_leave]

        self.__states.append(state_dict)
        self.__state_names.add(state)

    def add_global_transition(self, event, dst, on_before=None, on_after=None):
        return self.add_transition(
            event, self.__state_names, dst, on_before=on_before, on_after=on_after
        )

    def add_transition(
        self,
        event,
        src,
        dst,
        on_before=None,
        on_after=None,
        conditions=None,
        condition_target=True,
    ):
        event = to_name(event)

        src_states = to_list(src)
        src_state_names = [to_name(state) for state in src_states]

        dst = to_name(dst)

        for state_name in src_state_names:
            if state_name != ALL_STATES and state_name not in self.__state_names:
                raise Exception("Unknown source state:" + str(state_name))

        if dst != SAME_STATE and dst not in self.__state_names:
            raise Exception("Unknown destination state:" + str(dst))

        trigger_dict = {"trigger": event, "source": src_state_names, "dest": dst}

        if conditions:
            if condition_target:
                trigger_dict["conditions"] = conditions
            else:
                trigger_dict["unless"] = conditions

        if on_before:
            trigger_dict["before"] = on_before
        if on_after:
            trigger_dict["after"] = on_after

        self.__transitions.append(trigger_dict)

    def add_conditional_transition(
        self, event, src, condition, pass_dst, not_pass_dst=None
    ):
        self.add_transition(event, src, pass_dst, conditions=[condition])

        if not_pass_dst:
            self.add_transition(
                event, src, not_pass_dst, conditions=[condition], condition_target=False
            )

    def build(self):
        fsm = TransitionsFsmModel(self.__final)
        machine = Machine(
            model=fsm,
            states=self.__states,
            initial=self.__initial,
            transitions=self.__transitions,
            send_event=True,
            finalize_event=self.__transition_complete_callback,
        )
        fsm.init(machine)

        return fsm

    def draw(self, path, title="State Machine"):
        fsm = TransitionsFsmModel(self.__final)
        from transitions.extensions import GraphMachine

        machine = GraphMachine(
            model=fsm,
            states=self.__states,
            initial=self.__initial,
            transitions=self.__transitions,
            send_event=True,
            finalize_event=self.__transition_complete_callback,
            title=title,
            use_pygraphviz=True,
            show_conditions=True,
            show_state_attributes=True,
        )
        fsm.init(machine)
        fsm.get_graph().draw(path, prog="dot")
        return fsm
