import os


def test_draw_process_life_cycle():
    directory_path = os.path.dirname(os.path.abspath(__file__))
    file_name = "launch_state_diagram.png"
    file_path = os.path.join(directory_path, file_name)
    try:
        from util.process_life_cycle import ProcessLifeCycle

        process_life_cycle = ProcessLifeCycle(None)
        process_life_cycle.get_fsm_builder().draw(file_path)
        assert os.path.isfile(file_path) is True
    finally:
        try:
            os.remove(file_path)
        except OSError:
            assert "Unable to remove file. Please investigate."


def test_draw_config_life_cycle():
    directory_path = os.path.dirname(os.path.abspath(__file__))
    file_name = "config_cycle_state_diagram.png"
    file_path = os.path.join(directory_path, file_name)
    try:
        from util.config_life_cycle import ConfigLifeCycle

        config_life_cycle = ConfigLifeCycle(None, None, None, None)
        config_life_cycle.get_fsm_builder().draw(file_path)
        assert os.path.isfile(file_path) is True
    finally:
        try:
            os.remove(file_path)
        except OSError:
            assert "Unable to remove file. Please investigate."
