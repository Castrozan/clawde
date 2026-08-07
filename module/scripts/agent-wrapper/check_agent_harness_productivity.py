import argparse
import json
import sys

from active_harness import active_harness_name_for_launch_config
from clawde_runtime_layout import launch_config_path_for_agent, runtime_root_directory
from harness_failover import next_harness_after_refusal
from harness_productivity_record import (
    CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER,
    consecutive_unproductive_turns,
    harness_is_refusing_work,
    harness_productivity_record_path,
    read_harness_productivity_record,
)

PRODUCTIVE_EXIT_CODE = 0
REFUSING_WORK_EXIT_CODE = 1


def read_launch_config(launch_config_path: str) -> dict | None:
    try:
        with open(launch_config_path) as launch_config_file:
            return json.load(launch_config_file)
    except (OSError, ValueError):
        return None


def describe_refusing_harness(
    agent_name: str, harness_name: str, record: dict, next_harness_name: str | None
) -> str:
    remedy = (
        f"Its supervisor is moving it onto {next_harness_name}."
        if next_harness_name is not None
        else (
            "It has no fallback harness to move to, so it stays parked: give it a "
            f"harnessFallbackChain, or move it now with 'clawde harness {agent_name} "
            "<harness>'."
        )
    )
    return (
        f"{agent_name} is supervised on {harness_name} but produced nothing across "
        f"{consecutive_unproductive_turns(record)} consecutive heartbeats "
        f"(last productive turn: {record.get('last_productive_turn_at') or 'never'}). "
        f"{remedy}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check-agent-harness-productivity",
        description="Exit non-zero when a clawde agent has been prompted by its "
        "heartbeat and produced no turn "
        f"{CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER} times in a row, which is "
        "what a quota-exhausted or credential-refused provider looks like from "
        "outside: the process is alive and the pane sits at its idle prompt, so "
        "every liveness check passes while the agent does nothing.",
    )
    parser.add_argument(
        "--agent-name",
        required=True,
        help="Agent whose harness productivity record is read",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    launch_config_path = launch_config_path_for_agent(arguments.agent_name)
    launch_config = read_launch_config(launch_config_path)
    if launch_config is None:
        sys.exit(PRODUCTIVE_EXIT_CODE)

    harness_name = active_harness_name_for_launch_config(
        launch_config, launch_config_path
    )
    record = read_harness_productivity_record(
        harness_productivity_record_path(runtime_root_directory(), arguments.agent_name)
    )
    if not harness_is_refusing_work(record, harness_name):
        sys.exit(PRODUCTIVE_EXIT_CODE)

    print(
        describe_refusing_harness(
            arguments.agent_name,
            harness_name,
            record,
            next_harness_after_refusal(launch_config, harness_name),
        )
    )
    sys.exit(REFUSING_WORK_EXIT_CODE)


if __name__ == "__main__":
    main()
