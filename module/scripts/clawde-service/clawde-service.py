import argparse
import json
import time

import agent_wrapper_reconcile
from supervisor_backend_base import (
    SupervisorMultiplexerBackend,
    select_supervisor_backend,
)

SUPERVISOR_POLL_INTERVAL_SECONDS = 10
AGENT_STARTUP_STAGGER_SECONDS = 2


def ensure_agent_windows_for_session(
    backend: SupervisorMultiplexerBackend, session_specification: dict
) -> None:
    session_name = session_specification["name"]

    bootstrap_scaffolding_created = backend.ensure_host_ready(session_name)

    declared_agent_names = {
        agent_specification["name"]
        for agent_specification in session_specification["agents"]
    }
    agent_names_with_a_running_wrapper = (
        agent_wrapper_reconcile.agent_names_with_running_wrapper_after_reconcile(
            session_name, declared_agent_names
        )
    )

    for agent_specification in session_specification["agents"]:
        if agent_specification["name"] in agent_names_with_a_running_wrapper:
            continue
        agent_window_was_created = backend.ensure_agent_window(
            session_name,
            agent_specification["name"],
            agent_specification["wrapper_command"],
        )
        if agent_window_was_created:
            time.sleep(AGENT_STARTUP_STAGGER_SECONDS)

    if bootstrap_scaffolding_created:
        backend.remove_bootstrap_scaffolding(session_name)


def ensure_all_agent_windows(
    backend: SupervisorMultiplexerBackend, specification: dict
) -> None:
    for session_specification in specification["sessions"]:
        ensure_agent_windows_for_session(backend, session_specification)


def reconcile_sessions_forever(
    specification: dict,
    poll_interval_seconds: int = SUPERVISOR_POLL_INTERVAL_SECONDS,
) -> None:
    backend = select_supervisor_backend()
    while True:
        ensure_all_agent_windows(backend, specification)
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
