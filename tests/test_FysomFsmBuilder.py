from unittest import TestCase

from fsm.FysomFsmBuilder import FysomFsmBuilder


class TestFsmBuilder(TestCase):
    def test_add_initial_state(self):
        fsmBuilder = FysomFsmBuilder()
        fsmBuilder.add_initial_state("start")
        fsmBuilder.add_state("middle", on_leave=lambda e: print("left middle state" + e.args[0]['msg']))
        fsmBuilder.add_final_state("done", on_enter=lambda e: print("entered final state"))
        fsmBuilder.add_transition("move", "start", "middle", on_before=lambda e: print("before moving"), on_after=lambda e: print("after moving"))
        fsmBuilder.add_transition("stop", "middle", "done", on_before=lambda e: print("before stopping"), on_after=lambda e: print("after stopping"))
        fsm = fsmBuilder.build()
        print(fsm.current())
        fsm.trigger("move")
        print(fsm.current())
        fsm.trigger("stop", {'msg': 'Doneeeee'})
        print(fsm.current())
        print(fsm.is_complete())

    def raiseError(self, msg):
        raise ValueError(msg)
