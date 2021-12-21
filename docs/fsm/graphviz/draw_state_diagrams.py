from util.config_life_cycle import ConfigLifeCycle
from util.process_life_cycle import ProcessLifeCycle


def draw_state_diagram():
    process_life_cycle = ProcessLifeCycle(None)
    config_life_cycle = ConfigLifeCycle(None, None, None, None)

    process_life_cycle.get_fsm_builder().draw(
        "docs/fsm/graphviz/launch_state_diagram.png", title="Process Life Cycle"
    )
    config_life_cycle.get_fsm_builder().draw(
        "docs/fsm/graphviz/config_cycle_state_diagram.png",
        title="Configuration Life Cycle",
    )


if __name__ == "__main__":
    draw_state_diagram()
