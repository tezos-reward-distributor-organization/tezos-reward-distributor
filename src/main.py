from launch_common import (
    new_protocol_not_live,
    requirements_installed,
    renamed_fee_ini,
    python_version_ok,
)


def start_application(args=None):
    # Requirements need to be checked outside of the state machine
    # because the library transitions could not be present
    ready = (
        python_version_ok()
        and requirements_installed()
        and renamed_fee_ini()
        and new_protocol_not_live()
    )

    if ready:
        from util.process_life_cycle import ProcessLifeCycle

        life_cycle = ProcessLifeCycle(args)
        life_cycle.start()
        return 0
    else:
        return 1


if __name__ == "__main__":
    start_application()
