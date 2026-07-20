import argparse
import datetime

from clawde_runtime_layout import runtime_root_directory
from on_demand_decision import (
    agent_runs_on_demand,
    on_demand_configuration_for_agent,
    workspace_directory_for_agent,
)
from on_demand_lease import (
    clear_lease,
    lease_file_path_for_agent,
    read_lease_started_at,
    write_lease_started_at,
)
from session_persistence import session_conversation_exists
from session_store import build_session_record_file_path, read_persisted_session_record


def describe_resume_target(agent_name: str) -> str:
    session_identifier, _started_on_date = read_persisted_session_record(
        build_session_record_file_path(runtime_root_directory(), agent_name)
    )
    if session_conversation_exists(
        session_identifier, workspace_directory_for_agent(agent_name)
    ):
        return f"resuming session {session_identifier}"
    return "starting a fresh session"


def refuse_when_agent_is_not_on_demand(agent_name: str) -> None:
    if agent_runs_on_demand(agent_name):
        return
    raise SystemExit(
        f"Agent {agent_name} is not an on-demand agent, so the supervisor already "
        "owns whether it runs. Set onDemand = true on it to control it this way."
    )


def start_agent_on_demand(agent_name: str, now: datetime.datetime) -> None:
    refuse_when_agent_is_not_on_demand(agent_name)
    _on_demand, idle_timeout_minutes = on_demand_configuration_for_agent(agent_name)
    resume_description = describe_resume_target(agent_name)
    write_lease_started_at(
        lease_file_path_for_agent(runtime_root_directory(), agent_name), now
    )
    print(
        f"Started {agent_name} on demand ({resume_description}). "
        f"The supervisor brings it up within its next poll and stops it again "
        f"after {idle_timeout_minutes} minutes without conversation activity."
    )


def stop_agent_on_demand(agent_name: str) -> None:
    refuse_when_agent_is_not_on_demand(agent_name)
    lease_file_path = lease_file_path_for_agent(runtime_root_directory(), agent_name)
    if read_lease_started_at(lease_file_path) is None:
        print(f"Agent {agent_name} is already stopped.")
        return
    clear_lease(lease_file_path)
    print(
        f"Stopped {agent_name}. The supervisor tears its window down on its next "
        "poll, and its session is preserved for the next start."
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde start|stop",
        description="Start or stop an on-demand clawde agent. An on-demand agent is "
        "never brought up by the supervisor on its own; starting it grants a lease "
        "the supervisor honours until the agent has been idle past its timeout.",
    )
    parser.add_argument("action", choices=["start", "stop"])
    parser.add_argument("agent_name", help="Name of the on-demand agent")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.action == "stop":
        stop_agent_on_demand(arguments.agent_name)
        return
    start_agent_on_demand(arguments.agent_name, datetime.datetime.now())


if __name__ == "__main__":
    main()
