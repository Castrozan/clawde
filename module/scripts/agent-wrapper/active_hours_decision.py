import datetime
import json

from active_hours_override import (
    active_hours_gate_allows_run,
    override_file_path_for_agent,
    read_override_active_until,
)
from clawde_runtime_layout import (
    launch_config_path_for_agent,
    runtime_root_directory,
)
from restart_scheduling import is_within_active_hours


def read_active_hours_gate_configuration(
    launch_config_path: str,
) -> tuple[int | None, int | None, bool]:
    with open(launch_config_path) as launch_config_file:
        launch_config = json.load(launch_config_file)
    return (
        launch_config.get("active_hours_start"),
        launch_config.get("active_hours_end"),
        launch_config.get("active_weekdays_only", False),
    )


def agent_should_run_now(agent_name: str, now: datetime.datetime | None = None) -> bool:
    if now is None:
        now = datetime.datetime.now()
    try:
        active_hours_start, active_hours_end, active_weekdays_only = (
            read_active_hours_gate_configuration(
                launch_config_path_for_agent(agent_name)
            )
        )
    except (OSError, ValueError):
        return True
    within_active_hours = is_within_active_hours(
        active_hours_start, active_hours_end, now, active_weekdays_only
    )
    override_active_until = read_override_active_until(
        override_file_path_for_agent(runtime_root_directory(), agent_name)
    )
    return active_hours_gate_allows_run(within_active_hours, override_active_until, now)
