from unittest import TestCase


class TestProcessLifeCycle(TestCase):
    def test_draw(self):
        from util.process_life_cycle import ProcessLifeCycle
        life_cycle = ProcessLifeCycle({})
        life_cycle.get_fsm_builder().draw("launch_states.png")
