import os


def test_draw_process_life_cycle():
    try:
        from util.process_life_cycle import ProcessLifeCycle
        process_life_cycle = ProcessLifeCycle(None)
        process_life_cycle.get_fsm_builder().draw("launch_state_diagram.png")
        assert os.path.isfile("launch_state_diagram.png") is True
    finally:
        os.remove("launch_state_diagram.png")


def test_draw_config_life_cycle():
    try:
        from util.config_life_cycle import ConfigLifeCycle
        config_life_cycle = ConfigLifeCycle(None, None, None, None)
        config_life_cycle.get_fsm_builder().draw("config_cycle_state_diagram.png")
        assert os.path.isfile("config_cycle_state_diagram.png") is True
    finally:
        os.remove("config_cycle_state_diagram.png")
