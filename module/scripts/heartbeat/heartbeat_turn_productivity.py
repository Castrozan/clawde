import time

MINIMUM_PRODUCTIVE_TURN_SECONDS = 12


def delivered_turn_is_still_running(
    backend,
    pane_handle,
    harness_runtime_profile,
    sleep_function=time.sleep,
) -> bool:
    sleep_function(MINIMUM_PRODUCTIVE_TURN_SECONDS)
    return not backend.pane_is_idle(pane_handle, harness_runtime_profile)
