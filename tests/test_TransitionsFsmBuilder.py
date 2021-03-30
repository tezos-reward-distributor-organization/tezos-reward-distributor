from unittest import TestCase

from fsm.TransitionsFsmBuilder import TransitionsFsmBuilder


class TestFsmBuilder(TestCase):
    def test_add_initial_state(self):
        fsmBuilder = TransitionsFsmBuilder()
        fsmBuilder.add_initial_state("start")
        fsmBuilder.add_state("middle", on_leave=lambda e: print("left middle state: message=", e.args))
        fsmBuilder.add_state("running", on_enter=lambda e: print("Running", e))
        fsmBuilder.add_state("not_running", on_enter=lambda e: print("Not running", e))
        fsmBuilder.add_final_state("done", on_enter=lambda e: print("entered final state", e.kwargs.get('msg', 'None')))
        fsmBuilder.add_transition("move", "start", "middle", on_before=self.before_moving, on_after=self.after_moving)
        fsmBuilder.add_conditional_transition("run", "middle", self.is_tired, "not_running", "running")
        fsmBuilder.add_transition("stop", ["not_running", "running"], "done", on_before=self.before_stopping, on_after=self.after_stopping)

        fsm = fsmBuilder.build()

        fsm.trigger_event("move")
        self.assertEqual(fsm.current(), "middle")

        fsm.trigger_event("run", 'Run Forest')
        self.assertEqual(fsm.current(), "not_running")

        fsm.trigger_event("stop", msg='Stop There')
        self.assertTrue(fsm.is_complete())

    def test_exceptions(self):
        fsmBuilder = TransitionsFsmBuilder()
        fsmBuilder.add_transition_complete_callback(self.print_any_error)
        fsmBuilder.add_initial_state("start")
        fsmBuilder.add_state("middle", on_leave=lambda e: print("left middle state: message=", e.args))
        fsmBuilder.add_state("running", on_enter=lambda e: print("Running", e))
        fsmBuilder.add_state("not_running", on_enter=lambda e: print("Not running", e))
        fsmBuilder.add_final_state("done", on_enter=lambda e: print("entered final state", e.kwargs.get('msg', 'None'), 'error:', e.error))
        fsmBuilder.add_global_transition("fail", "done", on_before=lambda e: print("Processing failed", e))
        fsmBuilder.add_transition("move", "start", "middle", on_before=self.before_moving, on_after=self.after_moving)
        fsmBuilder.add_conditional_transition("run", "middle", self.is_tired, "not_running", "running")
        fsmBuilder.add_transition("stop", ["not_running", "running"], "done", on_before=self.raiseError, on_after=self.after_stopping)
        fsm = fsmBuilder.build()

        try:
            fsm.trigger_event("move")
            self.assertEqual(fsm.current(), "middle")

            fsm.trigger_event("run", 'Run Forest')
            self.assertEqual(fsm.current(), "not_running")

            fsm.trigger_event("stop", msg='Stop There')
            self.assertTrue(fsm.is_complete())
        except Exception:
            fsm.trigger_event("fail")
            self.assertTrue(fsm.is_complete())

    @staticmethod
    def print_any_error(e):
        if e.error:
            print("error during transition: ", type(e.error), e.error, "during transition from:", e.transition.source, " to:", e.transition.dest)

    @staticmethod
    def after_stopping(e):
        print("after stopping", e)

    @staticmethod
    def after_moving(e):
        print("after moving", e)

    @staticmethod
    def before_stopping(e):
        print("before stopping", e)

    @staticmethod
    def before_moving(e):
        print("before moving", e)

    def raiseError(self, msg):
        raise ValueError(msg)

    @staticmethod
    def is_tired(e):
        return True
