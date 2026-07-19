import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROBE_TIMEOUT_SECONDS = 180


def default_state_file(label: str) -> Path:
    state_home = os.environ.get("XDG_STATE_HOME") or os.path.expanduser(
        "~/.local/state"
    )
    return Path(state_home) / "clawde-heartbeat-change-gate" / label


def run_probe(probe_command: str) -> tuple[int, str]:
    completed = subprocess.run(
        ["bash", "-c", probe_command],
        capture_output=True,
        text=True,
        timeout=PROBE_TIMEOUT_SECONDS,
    )
    return completed.returncode, completed.stdout.strip()


def read_stored_state(state_file: Path) -> tuple[str | None, int]:
    if not state_file.is_file():
        return None, 0
    raw = state_file.read_text()
    try:
        stored = json.loads(raw)
    except ValueError:
        return raw, 1
    return stored.get("fingerprint"), stored.get("fire_count", 1)


def read_stored_fingerprint(state_file: Path) -> str | None:
    return read_stored_state(state_file)[0]


def store_fingerprint(state_file: Path, fingerprint: str, fire_count: int = 1) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps({"fingerprint": fingerprint, "fire_count": fire_count})
    )


def forget_fingerprint(state_file: Path) -> None:
    state_file.unlink(missing_ok=True)


def gate_fires(
    probe_command: str,
    state_file: Path,
    retries_while_pending: int = 0,
) -> bool:
    return_code, fingerprint = run_probe(probe_command)
    if return_code != 0 or not fingerprint:
        forget_fingerprint(state_file)
        return False

    stored_fingerprint, stored_fire_count = read_stored_state(state_file)
    if fingerprint != stored_fingerprint:
        store_fingerprint(state_file, fingerprint)
        return True
    if stored_fire_count > retries_while_pending:
        return False
    store_fingerprint(state_file, fingerprint, stored_fire_count + 1)
    return True


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-heartbeat-change-gate",
        description="Edge-triggered heartbeat gate any clawde agent can opt into. "
        "Run a probe command that prints the agent's current actionable fingerprint, "
        "and fire the tick (exit 0) only when that fingerprint differs from the last "
        "one fired. Empty probe output or a non-zero probe exit means nothing is "
        "actionable: skip the tick (exit 1) and forget the stored fingerprint so a "
        "later recurrence of the same state fires afresh. A steady actionable state is "
        "surfaced to the agent once, not every tick, so the agent spends no tokens "
        "re-deciding a state it already saw.",
    )
    parser.add_argument(
        "--label",
        required=True,
        help="Stable agent identifier used to namespace the stored fingerprint.",
    )
    parser.add_argument(
        "--probe",
        required=True,
        help="Shell command printing the current actionable fingerprint, or nothing "
        "when the agent has no reason to wake.",
    )
    parser.add_argument(
        "--retries-while-pending",
        type=int,
        default=0,
        help="How many extra times an unchanged actionable fingerprint may re-fire "
        "before the gate falls silent on it. The fingerprint is stored the moment the "
        "gate fires, not when the work completes, so a cycle that dies mid-task leaves "
        "an unchanged state a pure edge trigger never surfaces again; a small retry "
        "budget recovers that without restoring the old level-triggered behaviour, "
        "where a state only the operator could clear re-woke the agent every tick "
        "forever and burned tokens re-deriving the same decision. Default 0 keeps the "
        "gate purely edge-triggered.",
    )
    parser.add_argument(
        "--state-file",
        default=None,
        help="Override the fingerprint store path. Defaults to a per-label file under "
        "$XDG_STATE_HOME.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    state_file = (
        Path(arguments.state_file)
        if arguments.state_file
        else default_state_file(arguments.label)
    )
    return (
        0
        if gate_fires(arguments.probe, state_file, arguments.retries_while_pending)
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
