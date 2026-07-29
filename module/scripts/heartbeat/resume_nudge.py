import argparse
import os
import subprocess
import sys
import time

from harness_runtime_profile import load_harness_runtime_profile_from_launch_config
from multiplexer import select_heartbeat_backend

AGENT_WRAPPER_COMMAND_FRAGMENT = "agent-wrapper/wrapper.py --agent-name"
LIVE_AGENT_WAIT_MAX_ATTEMPTS = 20
LIVE_AGENT_WAIT_DELAY_SECONDS = 2
INHERITED_HERDR_PANE_ID_ENVIRONMENT_VARIABLE = "HERDR_PANE_ID"

RESUME_NUDGE_PROMPT = (
    "<resume>\n"
    "You were just restarted to apply a deployment; your previous session and full "
    "context were preserved and reloaded. Resume whatever task you had in flight from "
    "exactly where you left off, and tell the user you are back if a reply was "
    "pending. Do not re-run steps that already completed, and never trigger another "
    "rebuild or redeploy as a result of this message. If you had no task in progress, "
    "simply end your turn - idle is the correct outcome.\n"
    "</resume>\n"
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-resume-nudge",
        description="After a warm redeploy, wait for a clawde agent's REPL to come "
        "back and inject a one-shot prompt so the resumed agent continues its "
        "in-flight work instead of idling at the prompt.",
    )
    parser.add_argument("--session", required=True, help="multiplexer session name")
    parser.add_argument(
        "--window", required=True, help="multiplexer window/tab name (agent name)"
    )
    parser.add_argument(
        "--launch-config",
        required=True,
        help="Path to the agent's JSON launch config, read for the harness runtime "
        "profile that names this harness's process and prompt markers",
    )
    return parser.parse_args()


def find_agent_wrapper_process_id(agent_name: str) -> int | None:
    completed_process = subprocess.run(
        ["pgrep", "-f", f"{AGENT_WRAPPER_COMMAND_FRAGMENT} {agent_name}"],
        capture_output=True,
        text=True,
    )
    for line in completed_process.stdout.split():
        if line.strip().isdigit():
            return int(line)
    return None


def agent_wrapper_has_live_harness_child(
    wrapper_process_id: int, live_process_name_fragment: str
) -> bool:
    completed_process = subprocess.run(
        ["pgrep", "-P", str(wrapper_process_id), "-l"],
        capture_output=True,
        text=True,
    )
    return any(
        live_process_name_fragment in child_description
        for child_description in completed_process.stdout.splitlines()
        if child_description.strip()
    )


def agent_has_live_harness_repl(
    agent_name: str, live_process_name_fragment: str
) -> bool:
    wrapper_process_id = find_agent_wrapper_process_id(agent_name)
    if wrapper_process_id is None:
        return False
    return agent_wrapper_has_live_harness_child(
        wrapper_process_id, live_process_name_fragment
    )


def wait_for_live_harness_repl(
    agent_name: str, live_process_name_fragment: str
) -> bool:
    for _ in range(LIVE_AGENT_WAIT_MAX_ATTEMPTS):
        if agent_has_live_harness_repl(agent_name, live_process_name_fragment):
            return True
        time.sleep(LIVE_AGENT_WAIT_DELAY_SECONDS)
    return False


def discard_inherited_pane_id_so_target_resolves_by_agent_window_label() -> None:
    os.environ.pop(INHERITED_HERDR_PANE_ID_ENVIRONMENT_VARIABLE, None)


def main() -> None:
    arguments = parse_arguments()
    harness_runtime_profile = load_harness_runtime_profile_from_launch_config(
        arguments.launch_config
    )
    target_description = f"{arguments.session}:{arguments.window}"

    if not wait_for_live_harness_repl(
        arguments.window, harness_runtime_profile.live_process_name_fragment
    ):
        print(
            f"Agent {target_description} has no live "
            f"{harness_runtime_profile.harness_name} REPL (dormant or outside active "
            "hours); skipping resume nudge.",
            file=sys.stderr,
        )
        return

    discard_inherited_pane_id_so_target_resolves_by_agent_window_label()
    backend = select_heartbeat_backend()
    pane_handle = backend.prepare_pane_handle(arguments.session, arguments.window)
    if pane_handle is None:
        print(
            f"Error: could not resolve agent pane for {target_description}",
            file=sys.stderr,
        )
        sys.exit(1)

    backend.dismiss_pre_prompt_modal_if_present(pane_handle, harness_runtime_profile)

    if not backend.wait_for_agent_prompt(pane_handle, harness_runtime_profile):
        print(
            f"Error: {harness_runtime_profile.harness_name} REPL prompt not detected "
            f"for {target_description} after waiting; not injecting resume nudge.",
            file=sys.stderr,
        )
        sys.exit(1)

    backend.send_prompt_to_pane(pane_handle, RESUME_NUDGE_PROMPT)


if __name__ == "__main__":
    main()
