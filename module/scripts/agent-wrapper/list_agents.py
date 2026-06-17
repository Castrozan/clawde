import datetime

from active_hours_override import (
    override_file_path_for_agent,
    read_override_active_until,
)
from clawde_runtime_layout import (
    deployed_agent_names,
    launch_config_path_for_agent,
    read_active_hours_window,
    runtime_root_directory,
)

AGENT_COLUMN_HEADER = "AGENT"
ACTIVE_HOURS_COLUMN_HEADER = "ACTIVE HOURS"
OVERRIDE_COLUMN_HEADER = "OVERRIDE"
COLUMN_SEPARATOR = "  "
UNREADABLE_LAUNCH_CONFIG_MARKER = "unreadable"


def describe_active_hours_window(
    active_hours_start: int | None, active_hours_end: int | None
) -> str:
    if active_hours_start is None or active_hours_end is None:
        return "always-on"
    return f"{active_hours_start:02d}:00-{active_hours_end:02d}:00"


def describe_override_status(
    override_active_until: datetime.datetime | None, now: datetime.datetime
) -> str:
    if override_active_until is None:
        return "none"
    if now < override_active_until:
        return f"active until {override_active_until.isoformat(timespec='seconds')}"
    return "expired"


def describe_active_hours_for_agent(agent_name: str) -> str:
    try:
        active_hours_start, active_hours_end = read_active_hours_window(
            launch_config_path_for_agent(agent_name)
        )
    except (OSError, ValueError):
        return UNREADABLE_LAUNCH_CONFIG_MARKER
    return describe_active_hours_window(active_hours_start, active_hours_end)


def collect_agent_rows(now: datetime.datetime) -> list[dict[str, str]]:
    agent_rows = []
    for agent_name in deployed_agent_names():
        override_active_until = read_override_active_until(
            override_file_path_for_agent(runtime_root_directory(), agent_name)
        )
        agent_rows.append(
            {
                "agent": agent_name,
                "active_hours": describe_active_hours_for_agent(agent_name),
                "override": describe_override_status(override_active_until, now),
            }
        )
    return agent_rows


def format_agent_rows(agent_rows: list[dict[str, str]]) -> str:
    agent_column_width = max(
        [len(AGENT_COLUMN_HEADER)] + [len(row["agent"]) for row in agent_rows]
    )
    active_hours_column_width = max(
        [len(ACTIVE_HOURS_COLUMN_HEADER)]
        + [len(row["active_hours"]) for row in agent_rows]
    )
    header_line = COLUMN_SEPARATOR.join(
        [
            AGENT_COLUMN_HEADER.ljust(agent_column_width),
            ACTIVE_HOURS_COLUMN_HEADER.ljust(active_hours_column_width),
            OVERRIDE_COLUMN_HEADER,
        ]
    )
    row_lines = [
        COLUMN_SEPARATOR.join(
            [
                row["agent"].ljust(agent_column_width),
                row["active_hours"].ljust(active_hours_column_width),
                row["override"],
            ]
        )
        for row in agent_rows
    ]
    return "\n".join([header_line] + row_lines)


def main() -> None:
    print(format_agent_rows(collect_agent_rows(datetime.datetime.now())))


if __name__ == "__main__":
    main()
