import argparse
import datetime
import subprocess
import sys
import time

from cron import cron_expression_matches, seconds_until_next_minute_boundary
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
    cron_expression: str,
    prompt: str,
    gate_command: str | None,
) -> None:
    while True:
        time.sleep(seconds_until_next_minute_boundary(datetime.datetime.now()))
        now = datetime.datetime.now()
        if not cron_expression_matches(cron_expression, now):
            continue
        if not backend.pane_is_idle(pane_handle):
            continue
        if not gate_allows_wake(gate_command):
            continue
        backend.send_prompt_to_pane(pane_handle, prompt)


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

    backend = select_heartbeat_backend()
    pane_handle = backend.prepare_pane_handle(args.session, args.window)
    if pane_handle is None:
        print("Error: could not resolve agent pane", file=sys.stderr)
        sys.exit(1)

    if not backend.wait_for_claude_prompt(pane_handle):
        print(
            "Error: claude REPL prompt not detected after waiting. "
            "Agent may be stuck at onboarding. Not driving heartbeat.",
            file=sys.stderr,
        )
        sys.exit(1)

    drive_heartbeat(backend, pane_handle, args.interval, args.prompt, args.gate_command)


if __name__ == "__main__":
    main()
