import datetime
import json
import os

ON_DEMAND_LEASE_SUBDIRECTORY = "on-demand"


def lease_file_path_for_agent(runtime_root_directory: str, agent_name: str) -> str:
    return os.path.join(
        runtime_root_directory,
        ON_DEMAND_LEASE_SUBDIRECTORY,
        f"{agent_name}.json",
    )


def read_lease_started_at(lease_file_path: str) -> datetime.datetime | None:
    try:
        with open(lease_file_path) as lease_file:
            stored_started_at = json.load(lease_file)["started_at"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        return datetime.datetime.fromisoformat(stored_started_at)
    except (ValueError, TypeError):
        return None


def write_lease_started_at(lease_file_path: str, started_at: datetime.datetime) -> None:
    os.makedirs(os.path.dirname(lease_file_path), exist_ok=True)
    with open(lease_file_path, "w") as lease_file:
        json.dump({"started_at": started_at.isoformat()}, lease_file)


def clear_lease(lease_file_path: str) -> None:
    try:
        os.remove(lease_file_path)
    except FileNotFoundError:
        pass


def latest_activity_time(
    lease_started_at: datetime.datetime,
    transcript_modified_at: datetime.datetime | None,
) -> datetime.datetime:
    if transcript_modified_at is None:
        return lease_started_at
    return max(lease_started_at, transcript_modified_at)


def lease_has_gone_idle(
    latest_activity_at: datetime.datetime,
    idle_timeout_minutes: int,
    now: datetime.datetime,
) -> bool:
    idle_deadline = latest_activity_at + datetime.timedelta(
        minutes=idle_timeout_minutes
    )
    return now >= idle_deadline
