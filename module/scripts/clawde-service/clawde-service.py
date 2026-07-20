import argparse
import json
import time

import active_hours_decision
import agent_wrapper_reconcile
import launch_gate_decision
import on_demand_decision
from supervisor_backend_base import (
    SupervisorMultiplexerBackend,
    select_supervisor_backend,
)

SUPERVISOR_POLL_INTERVAL_SECONDS = 10
AGENT_STARTUP_STAGGER_SECONDS = 2


def agent_should_be_running(
    agent_name: str,
    agent_has_a_live_wrapper: bool,
    launch_gate_scheduler: launch_gate_decision.LaunchGateScheduler,
) -> bool:
    if not active_hours_decision.agent_should_run_now(agent_name):
        return False
    if on_demand_decision.agent_runs_on_demand(agent_name):
        return on_demand_decision.agent_lease_allows_run(agent_name)
    if not launch_gate_decision.agent_launches_on_trigger(agent_name):
        return True
    if agent_has_a_live_wrapper:
        return True
    return launch_gate_scheduler.launch_is_pending(agent_name)


def ensure_agent_windows_for_session(
    backend: SupervisorMultiplexerBackend,
    session_specification: dict,
    launch_gate_scheduler: launch_gate_decision.LaunchGateScheduler,
) -> None:
    session_name = session_specification["name"]

    bootstrap_scaffolding_created = backend.ensure_host_ready(session_name)

    agent_names_with_a_live_wrapper = (
        agent_wrapper_reconcile.agent_names_with_live_wrapper(session_name)
    )
    agent_names_that_should_be_running = {
        agent_specification["name"]
        for agent_specification in session_specification["agents"]
        if agent_should_be_running(
            agent_specification["name"],
            agent_specification["name"] in agent_names_with_a_live_wrapper,
            launch_gate_scheduler,
        )
    }
    agent_names_with_a_running_wrapper = (
        agent_wrapper_reconcile.agent_names_with_running_wrapper_after_reconcile(
            session_name, agent_names_that_should_be_running
        )
    )

    for agent_specification in session_specification["agents"]:
        agent_name = agent_specification["name"]
        if agent_name not in agent_names_that_should_be_running:
            backend.remove_agent_window(session_name, agent_name)
            continue
        if agent_name in agent_names_with_a_running_wrapper:
            launch_gate_scheduler.consume_pending_launch(agent_name)
            continue
        agent_window_was_created = backend.ensure_agent_window(
            session_name,
            agent_name,
            agent_specification["wrapper_command"],
        )
        if agent_window_was_created:
            time.sleep(AGENT_STARTUP_STAGGER_SECONDS)

    if bootstrap_scaffolding_created:
        backend.remove_bootstrap_scaffolding(session_name)


def ensure_all_agent_windows(
    backend: SupervisorMultiplexerBackend,
    specification: dict,
    launch_gate_scheduler: launch_gate_decision.LaunchGateScheduler,
) -> None:
    for session_specification in specification["sessions"]:
        ensure_agent_windows_for_session(
            backend, session_specification, launch_gate_scheduler
        )


def reconcile_sessions_forever(
    specification: dict,
    poll_interval_seconds: int = SUPERVISOR_POLL_INTERVAL_SECONDS,
) -> None:
    backend = select_supervisor_backend()
    launch_gate_scheduler = launch_gate_decision.LaunchGateScheduler()
    while True:
        ensure_all_agent_windows(backend, specification, launch_gate_scheduler)
        time.sleep(poll_interval_seconds)


def load_specification(specification_file_path: str) -> dict:
    with open(specification_file_path) as specification_file:
        return json.load(specification_file)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-service",
        description=(
            "Idempotently ensure every declared clawde session and all agent windows "
            "exist on the configured multiplexer backend, then reconcile forever so "
            "any session or window that dies after startup gets recreated on the next "
            "poll."
        ),
    )
    parser.add_argument(
        "--specification-file",
        required=True,
        help="Path to JSON file describing the sessions and their agents",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    specification = load_specification(arguments.specification_file)
    reconcile_sessions_forever(specification)


if __name__ == "__main__":
    main()
