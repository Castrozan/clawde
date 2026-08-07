import argparse
import datetime
import subprocess
import sys
import time

from active_harness import runtime_root_directory_from_launch_config_path
from cron import cron_expression_matches, seconds_until_next_minute_boundary
from harness_productivity_record import (
    begin_harness_productivity_record,
    harness_productivity_record_path,
    record_observed_heartbeat_turn,
)
from harness_runtime_profile import load_harness_runtime_profile_from_launch_config
from heartbeat_turn_productivity import delivered_turn_is_still_running
from multiplexer import select_heartbeat_backend
from pane_content import HeartbeatMultiplexerBackend

GATE_TIMEOUT_SECONDS = 120


def gate_allows_wake(gate_command: str | None) -> bool:
    if not gate_command:
        return True
    try:
        result = subprocess.run(
            ["bash", "-c", gate_command],
            capture_output=True,
            text=True,
            timeout=GATE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def drive_heartbeat(
    backend: HeartbeatMultiplexerBackend,
    pane_handle,
    harness_runtime_profile,
    cron_expression: str,
    prompt: str,
    gate_command: str | None,
    productivity_record_path: str,
) -> None:
    while True:
        time.sleep(seconds_until_next_minute_boundary(datetime.datetime.now()))
        now = datetime.datetime.now()
        if not cron_expression_matches(cron_expression, now):
            continue
        if not backend.pane_is_idle(pane_handle, harness_runtime_profile):
            continue
        if not gate_allows_wake(gate_command):
            continue
        backend.send_prompt_to_pane(pane_handle, prompt)
        record_observed_heartbeat_turn(
            productivity_record_path,
            delivered_turn_is_still_running(
                backend, pane_handle, harness_runtime_profile
            ),
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-heartbeat-driver",
        description="Drive a clawde agent's heartbeat from outside the LLM: on each "
        "cron-matched minute run an optional deterministic gate and paste the "
        "heartbeat prompt into the agent pane only when the gate allows it.",
    )
    parser.add_argument("--session", required=True, help="multiplexer session name")
    parser.add_argument(
        "--window", required=True, help="multiplexer window/tab name (agent name)"
    )
    parser.add_argument(
        "--launch-config",
        required=True,
        help="Path to the agent's JSON launch config, read for the harness runtime "
        "profile that says how to recognize this harness's idle prompt and modals",
    )
    parser.add_argument(
        "--interval", required=True, help="Cron expression for heartbeat interval"
    )
    parser.add_argument(
        "--prompt", required=True, help="Prompt pasted into the pane on each fired tick"
    )
    parser.add_argument(
        "--gate-command",
        default=None,
        help="Shell command run before each tick; exit 0 fires the tick, non-zero skips it",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_arguments()
    harness_runtime_profile = load_harness_runtime_profile_from_launch_config(
        args.launch_config
    )

    productivity_record_path = harness_productivity_record_path(
        runtime_root_directory_from_launch_config_path(args.launch_config),
        args.window,
    )
    begin_harness_productivity_record(
        productivity_record_path, harness_runtime_profile.harness_name
    )

    backend = select_heartbeat_backend()
    pane_handle = backend.prepare_pane_handle(args.session, args.window)
    if pane_handle is None:
        print("Error: could not resolve agent pane", file=sys.stderr)
        sys.exit(1)

    if not backend.wait_until_agent_is_past_pre_prompt_gates(
        pane_handle, harness_runtime_profile
    ):
        print(
            f"Error: {harness_runtime_profile.harness_name} did not get past "
            "onboarding or a pre-prompt modal after waiting; it is wedged at a "
            "pre-prompt gate. Not driving heartbeat.",
            file=sys.stderr,
        )
        sys.exit(1)

    drive_heartbeat(
        backend,
        pane_handle,
        harness_runtime_profile,
        args.interval,
        args.prompt,
        args.gate_command,
        productivity_record_path,
    )


if __name__ == "__main__":
    main()
