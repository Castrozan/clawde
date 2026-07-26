import argparse
import datetime
import sys

from active_hours_decision import (
    agent_should_run_now,
    read_active_hours_gate_configuration,
)
from clawde_runtime_layout import (
    launch_config_path_for_agent,
    runtime_root_directory,
)
from on_demand_decision import (
    agent_runs_on_demand,
    last_conversation_activity_for_agent,
    on_demand_configuration_for_agent,
)
from on_demand_lease import (
    latest_activity_time,
    lease_file_path_for_agent,
    lease_has_gone_idle,
    read_lease_started_at,
)

WEEKEND_FIRST_ISO_WEEKDAY = 6
WEEKEND_DORMANCY_REASON = "weekday-only agent, weekend"
ON_DEMAND_NOT_STARTED_REASON = "on demand, not started"
OUTSIDE_ACTIVE_WINDOW_REASON = "outside active window"


def on_demand_lease_is_live(agent_name: str, now: datetime.datetime) -> bool:
    lease_started_at = read_lease_started_at(
        lease_file_path_for_agent(runtime_root_directory(), agent_name)
    )
    if lease_started_at is None:
        return False
    _on_demand, idle_timeout_minutes = on_demand_configuration_for_agent(agent_name)
    latest_activity_at = latest_activity_time(
        lease_started_at, last_conversation_activity_for_agent(agent_name)
    )
    return not lease_has_gone_idle(latest_activity_at, idle_timeout_minutes, now)


def inactive_window_reason(agent_name: str, now: datetime.datetime) -> str:
    try:
        active_hours_start, active_hours_end, active_weekdays_only = (
            read_active_hours_gate_configuration(
                launch_config_path_for_agent(agent_name)
            )
        )
    except (OSError, ValueError):
        return OUTSIDE_ACTIVE_WINDOW_REASON
    if active_weekdays_only and now.isoweekday() >= WEEKEND_FIRST_ISO_WEEKDAY:
        return WEEKEND_DORMANCY_REASON
    return f"outside active hours {active_hours_start}-{active_hours_end}"


def dormancy_reason_for_agent(
    agent_name: str, now: datetime.datetime | None = None
) -> str | None:
    if now is None:
        now = datetime.datetime.now()
    if not agent_should_run_now(agent_name, now):
        return inactive_window_reason(agent_name, now)
    if agent_runs_on_demand(agent_name) and not on_demand_lease_is_live(
        agent_name, now
    ):
        return ON_DEMAND_NOT_STARTED_REASON
    return None


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exit 0 when the supervisor is expected to be holding a process for the "
            "agent right now. Exit 1 and print why when the agent is dormant by "
            "design, so a liveness probe can skip itself instead of reporting a "
            "failure."
        )
    )
    parser.add_argument(
        "--agent-name",
        required=True,
        help="Name of the clawde agent to evaluate",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    dormancy_reason = dormancy_reason_for_agent(arguments.agent_name)
    if dormancy_reason is None:
        return 0
    print(dormancy_reason)
    return 1


if __name__ == "__main__":
    sys.exit(main())
