import datetime
import json
import os

ACTIVE_HOURS_OVERRIDE_SUBDIRECTORY = "active-hours-override"


def runtime_root_directory_from_launch_config_path(config_file_path: str) -> str:
    return os.path.dirname(os.path.dirname(config_file_path))


def override_file_path_for_agent(runtime_root_directory: str, agent_name: str) -> str:
    return os.path.join(
        runtime_root_directory,
        ACTIVE_HOURS_OVERRIDE_SUBDIRECTORY,
        f"{agent_name}.json",
    )


def read_override_active_until(override_file_path: str) -> datetime.datetime | None:
    try:
        with open(override_file_path) as override_file:
            stored_active_until = json.load(override_file)["active_until"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        return datetime.datetime.fromisoformat(stored_active_until)
    except (ValueError, TypeError):
        return None


def write_override_active_until(
    override_file_path: str, active_until: datetime.datetime
) -> None:
    os.makedirs(os.path.dirname(override_file_path), exist_ok=True)
    with open(override_file_path, "w") as override_file:
        json.dump({"active_until": active_until.isoformat()}, override_file)


def clear_override(override_file_path: str) -> None:
    try:
        os.remove(override_file_path)
    except FileNotFoundError:
        pass


def is_override_active(
    override_active_until: datetime.datetime | None, now: datetime.datetime
) -> bool:
    return override_active_until is not None and now < override_active_until


def active_hours_gate_allows_run(
    within_active_hours: bool,
    override_active_until: datetime.datetime | None,
    now: datetime.datetime,
) -> bool:
    return within_active_hours or is_override_active(override_active_until, now)


def override_is_stale(
    within_active_hours: bool,
    override_active_until: datetime.datetime | None,
    now: datetime.datetime,
) -> bool:
    if override_active_until is None:
        return False
    if within_active_hours:
        return True
    return not is_override_active(override_active_until, now)
