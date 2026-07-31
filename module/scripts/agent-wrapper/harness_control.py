import argparse
import json
import os
import signal

from active_harness import (
    active_harness_name_for_launch_config,
    clear_override,
    declared_harness_name,
    eligible_harness_names,
    override_file_path_for_agent,
    write_overridden_harness_name,
)
from agent_wrapper_processes import find_wrapper_process_id_for_agent
from clawde_runtime_layout import (
    deployed_agent_names,
    launch_config_path_for_agent,
    runtime_root_directory,
)


def load_launch_config(agent_name: str) -> dict:
    launch_config_path = launch_config_path_for_agent(agent_name)
    try:
        with open(launch_config_path) as launch_config_file:
            return json.load(launch_config_file)
    except OSError:
        raise SystemExit(
            f"Agent {agent_name} has no deployed launch config at "
            f"{launch_config_path}. Deployed agents: "
            f"{', '.join(deployed_agent_names()) or 'none'}."
        )


def active_harness_for_agent(agent_name: str, launch_config: dict) -> str:
    return active_harness_name_for_launch_config(
        launch_config, launch_config_path_for_agent(agent_name)
    )


def describe_one_agent(agent_name: str, launch_config: dict) -> str:
    declared = declared_harness_name(launch_config)
    active = active_harness_for_agent(agent_name, launch_config)
    overridden_marker = "" if active == declared else f" (overriding {declared})"
    return f"{agent_name}: {active}{overridden_marker}"


def show_every_agent_harness() -> None:
    agent_names = deployed_agent_names()
    if not agent_names:
        raise SystemExit("No clawde agents are deployed on this machine.")
    for agent_name in agent_names:
        print(describe_one_agent(agent_name, load_launch_config(agent_name)))


def show_one_agent_harness(agent_name: str) -> None:
    launch_config = load_launch_config(agent_name)
    print(describe_one_agent(agent_name, launch_config))
    print(f"eligible: {', '.join(eligible_harness_names(launch_config))}")


def refuse_ineligible_harness(agent_name: str, launch_config: dict, harness_name: str):
    eligible = eligible_harness_names(launch_config)
    if harness_name in eligible:
        return
    raise SystemExit(
        f"Agent {agent_name} cannot run on harness '{harness_name}'. It is eligible "
        f"for {', '.join(eligible)}. A harness drops off that list when it is not "
        "installed, when it cannot transport the agent's channel, or when it cannot "
        "enforce the agent's deny patterns."
    )


def restart_agent_onto_active_harness(agent_name: str) -> str:
    wrapper_process_id = find_wrapper_process_id_for_agent(agent_name)
    if wrapper_process_id is None:
        return "It starts on that harness the next time the supervisor brings it up."
    try:
        os.kill(wrapper_process_id, signal.SIGUSR1)
    except ProcessLookupError:
        return "It starts on that harness the next time the supervisor brings it up."
    return "Its running session was signalled to restart onto that harness now."


def set_agent_harness(agent_name: str, harness_name: str) -> None:
    launch_config = load_launch_config(agent_name)
    refuse_ineligible_harness(agent_name, launch_config, harness_name)
    write_overridden_harness_name(
        override_file_path_for_agent(runtime_root_directory(), agent_name),
        harness_name,
    )
    print(
        f"Agent {agent_name} now runs on {harness_name}. "
        f"{restart_agent_onto_active_harness(agent_name)}"
    )


def clear_agent_harness_override(agent_name: str) -> None:
    launch_config = load_launch_config(agent_name)
    declared = declared_harness_name(launch_config)
    clear_override(override_file_path_for_agent(runtime_root_directory(), agent_name))
    print(
        f"Agent {agent_name} returns to its declared harness {declared}. "
        f"{restart_agent_onto_active_harness(agent_name)}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde harness",
        description="Show or switch the harness a deployed clawde agent runs on. "
        "The switch is a runtime override stored beside the agent's launch config, "
        "so it survives a rebuild and is reverted with --clear rather than by "
        "editing nix. An agent may only move to a harness the deployment already "
        "materialized a config for.",
    )
    parser.add_argument(
        "agent_name",
        nargs="?",
        help="Agent to show or switch. Omit to list every deployed agent.",
    )
    parser.add_argument(
        "harness_name",
        nargs="?",
        help="Harness to switch the agent onto. Omit to show its current harness.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Drop the override and return the agent to its declared harness.",
    )
    parser.add_argument(
        "--eligible",
        action="store_true",
        help="Print one eligible harness name per line, for shell completion.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.agent_name is None:
        show_every_agent_harness()
        return
    if arguments.eligible:
        print(
            "\n".join(eligible_harness_names(load_launch_config(arguments.agent_name)))
        )
        return
    if arguments.clear:
        clear_agent_harness_override(arguments.agent_name)
        return
    if arguments.harness_name is None:
        show_one_agent_harness(arguments.agent_name)
        return
    set_agent_harness(arguments.agent_name, arguments.harness_name)


if __name__ == "__main__":
    main()
