import os


def test_draw_process_life_cycle():
    try:
        from util.process_life_cycle import ProcessLifeCycle
        process_life_cycle = ProcessLifeCycle(None)
        process_life_cycle.get_fsm_builder().draw("/tmp/launch_state_diagram.png")
        assert os.path.isfile("/tmp/launch_state_diagram.png") is True
    finally:
        os.remove("/tmp/launch_state_diagram.png")


def test_draw_config_life_cycle():
    try:
        from util.config_life_cycle import ConfigLifeCycle
        config_life_cycle = ConfigLifeCycle(None, None, None, None)
        config_life_cycle.get_fsm_builder().draw("/tmp/config_cycle_state_diagram.png")
        assert os.path.isfile("/tmp/config_cycle_state_diagram.png") is True
    finally:
        os.remove("/tmp/config_cycle_state_diagram.png")
