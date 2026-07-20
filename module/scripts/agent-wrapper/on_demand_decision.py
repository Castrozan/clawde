import datetime
import json

from clawde_runtime_layout import (
    launch_config_path_for_agent,
    runtime_root_directory,
)
from on_demand_lease import (
    clear_lease,
    lease_file_path_for_agent,
    lease_has_gone_idle,
    latest_activity_time,
    read_lease_started_at,
)
from session_persistence import session_conversation_modified_at
from session_store import build_session_record_file_path, read_persisted_session_record

DEFAULT_IDLE_TIMEOUT_MINUTES = 30


def read_on_demand_configuration(launch_config_path: str) -> tuple[bool, int]:
    with open(launch_config_path) as launch_config_file:
        launch_config = json.load(launch_config_file)
    return (
        launch_config.get("on_demand", False),
        launch_config.get("idle_timeout_minutes") or DEFAULT_IDLE_TIMEOUT_MINUTES,
    )


def read_workspace_directory(launch_config_path: str) -> str | None:
    with open(launch_config_path) as launch_config_file:
        return json.load(launch_config_file).get("workspace_directory")


def on_demand_configuration_for_agent(agent_name: str) -> tuple[bool, int]:
    try:
        return read_on_demand_configuration(launch_config_path_for_agent(agent_name))
    except (OSError, ValueError):
        return (False, DEFAULT_IDLE_TIMEOUT_MINUTES)


def agent_runs_on_demand(agent_name: str) -> bool:
    on_demand, _idle_timeout_minutes = on_demand_configuration_for_agent(agent_name)
    return on_demand


def workspace_directory_for_agent(agent_name: str) -> str | None:
    try:
        return read_workspace_directory(launch_config_path_for_agent(agent_name))
    except (OSError, ValueError):
        return None


def last_conversation_activity_for_agent(
    agent_name: str,
) -> datetime.datetime | None:
    session_identifier, _started_on_date = read_persisted_session_record(
        build_session_record_file_path(runtime_root_directory(), agent_name)
    )
    return session_conversation_modified_at(
        session_identifier, workspace_directory_for_agent(agent_name)
    )


def agent_lease_allows_run(
    agent_name: str, now: datetime.datetime | None = None
) -> bool:
    if now is None:
        now = datetime.datetime.now()
    lease_file_path = lease_file_path_for_agent(runtime_root_directory(), agent_name)
    lease_started_at = read_lease_started_at(lease_file_path)
    if lease_started_at is None:
        return False
    _on_demand, idle_timeout_minutes = on_demand_configuration_for_agent(agent_name)
    latest_activity_at = latest_activity_time(
        lease_started_at, last_conversation_activity_for_agent(agent_name)
    )
    if lease_has_gone_idle(latest_activity_at, idle_timeout_minutes, now):
        clear_lease(lease_file_path)
        return False
    return True
