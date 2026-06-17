import argparse
import datetime
import json
import os
import signal
import subprocess

from active_hours_override import (
    clear_override,
    override_file_path_for_agent,
    write_override_active_until,
)
from restart_scheduling import seconds_until_active_hours_start

RUNTIME_ROOT_RELATIVE_TO_HOME = "clawde"
LAUNCH_CONFIG_SUBDIRECTORY = "launch-config"


def runtime_root_directory() -> str:
    return os.path.join(os.path.expanduser("~"), RUNTIME_ROOT_RELATIVE_TO_HOME)


def launch_config_path_for_agent(agent_name: str) -> str:
    return os.path.join(
        runtime_root_directory(),
        LAUNCH_CONFIG_SUBDIRECTORY,
        f"{agent_name}.json",
    )


def read_active_hours_start(launch_config_path: str) -> int | None:
    with open(launch_config_path) as launch_config_file:
        return json.load(launch_config_file).get("active_hours_start")


def find_agent_wrapper_process_ids(agent_name: str) -> list[int]:
    completed_process = subprocess.run(
        [
            "pgrep",
            "-f",
            f"agent-wrapper/wrapper.py --agent-name {agent_name} --config-file",
        ],
        capture_output=True,
        text=True,
    )
    return [
        int(line) for line in completed_process.stdout.split() if line.strip().isdigit()
    ]


def signal_agent_wrapper_to_restart(agent_name: str) -> int:
    process_ids = find_agent_wrapper_process_ids(agent_name)
    for process_id in process_ids:
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
    return len(process_ids)


def clear_active_hours_override(agent_name: str) -> None:
    clear_override(override_file_path_for_agent(runtime_root_directory(), agent_name))
    signalled_process_count = signal_agent_wrapper_to_restart(agent_name)
    print(
        f"Cleared active-hours override for {agent_name}. "
        f"Signalled {signalled_process_count} wrapper process(es) to re-evaluate."
    )


def set_active_hours_override(agent_name: str, now: datetime.datetime) -> None:
    launch_config_path = launch_config_path_for_agent(agent_name)
    try:
        active_hours_start = read_active_hours_start(launch_config_path)
    except (OSError, ValueError) as launch_config_error:
        raise SystemExit(
            f"Could not read launch config for {agent_name} at "
            f"{launch_config_path}: {launch_config_error}"
        )
    if active_hours_start is None:
        print(
            f"Agent {agent_name} has no active-hours gate "
            "(active_hours_start is null); nothing to override."
        )
        return

    active_until = now + datetime.timedelta(
        seconds=seconds_until_active_hours_start(active_hours_start, now=now)
    )
    write_override_active_until(
        override_file_path_for_agent(runtime_root_directory(), agent_name),
        active_until,
    )
    signalled_process_count = signal_agent_wrapper_to_restart(agent_name)
    print(
        f"Active-hours override set for {agent_name} until {active_until.isoformat()} "
        f"(next active-hours start). "
        f"Signalled {signalled_process_count} wrapper process(es) to restart."
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-active-now",
        description="Temporarily override a clawde agent's active-hours gate so it runs "
        "now through the next active-hours start, then reverts to its normal window. "
        "Writes a runtime override file and restarts the agent's wrapper to apply it.",
    )
    parser.add_argument(
        "agent_name",
        help="Name of the agent whose active-hours gate to override",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Cancel an active override and let the agent return to its normal hours",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.clear:
        clear_active_hours_override(arguments.agent_name)
        return
    set_active_hours_override(arguments.agent_name, datetime.datetime.now())


if __name__ == "__main__":
    main()
