import os


def test_draw_process_life_cycle():
    directory_path = os.path.dirname(os.path.abspath(__file__))
    file_name = "launch_state_diagram"
    file_extension = ".png"
    file_path_1 = os.path.join(directory_path, file_name+file_extension)
    file_path_2 = os.path.join(directory_path, file_name)
    try:
        from util.process_life_cycle import ProcessLifeCycle

        process_life_cycle = ProcessLifeCycle(None)
        process_life_cycle.get_fsm_builder().draw(file_path_1)
        assert os.path.isfile(file_path_1) is True
    finally:
        if os.path.isfile(file_path_1):
            os.remove(file_path_1)
        if os.path.isfile(file_path_2):
            os.remove(file_path_2)


def test_draw_config_life_cycle():
    directory_path = os.path.dirname(os.path.abspath(__file__))
    file_name = "config_cycle_state_diagram"
    file_extension = ".png"
    file_path_1 = os.path.join(directory_path, file_name+file_extension)
    file_path_2 = os.path.join(directory_path, file_name)
    try:
        from util.config_life_cycle import ConfigLifeCycle

        config_life_cycle = ConfigLifeCycle(None, None, None, None)
        config_life_cycle.get_fsm_builder().draw(file_path_1)
        assert os.path.isfile(file_path_1) is True
    finally:
        if os.path.isfile(file_path_1):
            os.remove(file_path_1)
        if os.path.isfile(file_path_2):
            os.remove(file_path_2)
