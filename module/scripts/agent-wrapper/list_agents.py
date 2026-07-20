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
from on_demand_decision import agent_runs_on_demand
from on_demand_lease import lease_file_path_for_agent, read_lease_started_at

AGENT_TABLE_COLUMNS = [
    ("AGENT", "agent"),
    ("ACTIVE HOURS", "active_hours"),
    ("OVERRIDE", "override"),
    ("ON DEMAND", "on_demand"),
]
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


def describe_on_demand_status(agent_name: str) -> str:
    if not agent_runs_on_demand(agent_name):
        return "supervised"
    lease_started_at = read_lease_started_at(
        lease_file_path_for_agent(runtime_root_directory(), agent_name)
    )
    if lease_started_at is None:
        return "stopped"
    return f"started {lease_started_at.isoformat(timespec='seconds')}"


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
                "on_demand": describe_on_demand_status(agent_name),
            }
        )
    return agent_rows


def column_widths_for_rows(agent_rows: list[dict[str, str]]) -> list[int]:
    return [
        max([len(column_header)] + [len(row[row_key]) for row in agent_rows])
        for column_header, row_key in AGENT_TABLE_COLUMNS
    ]


def format_table_line(cells: list[str], column_widths: list[int]) -> str:
    padded_leading_cells = [
        cell.ljust(width) for cell, width in zip(cells[:-1], column_widths[:-1])
    ]
    return COLUMN_SEPARATOR.join(padded_leading_cells + cells[-1:])


def format_agent_rows(agent_rows: list[dict[str, str]]) -> str:
    column_widths = column_widths_for_rows(agent_rows)
    table_lines = [[column_header for column_header, _ in AGENT_TABLE_COLUMNS]] + [
        [row[row_key] for _, row_key in AGENT_TABLE_COLUMNS] for row in agent_rows
    ]
    return "\n".join(format_table_line(cells, column_widths) for cells in table_lines)


def main() -> None:
    print(format_agent_rows(collect_agent_rows(datetime.datetime.now())))


if __name__ == "__main__":
    main()
