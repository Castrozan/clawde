import argparse
import os
import signal
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_REBUILD_LOCK_DIRECTORY = Path("/tmp/dotfiles-rebuild.lock.d")
DEFAULT_POLL_INTERVAL_SECONDS = 1.0


def process_is_running(process_id):
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def owner_process_id(owner_metadata):
    for line in owner_metadata.splitlines():
        key, separator, value = line.partition("=")
        if key == "pid" and separator and value.isdecimal() and int(value) > 0:
            return int(value)
    return None


def rebuild_is_running(lock_directory):
    if not lock_directory.is_dir():
        return False
    try:
        owner_metadata = (lock_directory / "owner").read_text()
    except FileNotFoundError:
        return lock_directory.is_dir()
    process_id = owner_process_id(owner_metadata)
    return process_id is None or process_is_running(process_id)


def wait_until_rebuild_finishes(lock_directory, poll_interval_seconds):
    waiting_was_reported = False
    while rebuild_is_running(lock_directory):
        if not waiting_was_reported:
            print(
                f"steward validation waiting for {lock_directory}",
                file=sys.stderr,
                flush=True,
            )
            waiting_was_reported = True
        time.sleep(poll_interval_seconds)
    if waiting_was_reported:
        print("operator rebuild finished; starting steward validation", file=sys.stderr)


def lower_cpu_priority():
    os.nice(19)


def low_io_priority_command(command):
    ionice_binary = shutil.which("ionice")
    if ionice_binary:
        return [ionice_binary, "-c", "3", *command]
    return command


def start_validation_process(command):
    return subprocess.Popen(low_io_priority_command(command), start_new_session=True)


def terminate_validation_process(validation_process):
    try:
        os.killpg(validation_process.pid, signal.SIGTERM)
    except ProcessLookupError:
        validation_process.wait()
        return
    try:
        validation_process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(validation_process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        validation_process.wait()


def run_validation_with_rebuild_preemption(
    command,
    lock_directory,
    poll_interval_seconds,
):
    lower_cpu_priority()
    while True:
        wait_until_rebuild_finishes(lock_directory, poll_interval_seconds)
        validation_process = start_validation_process(command)
        validation_is_running = True
        try:
            while True:
                try:
                    exit_code = validation_process.wait(timeout=poll_interval_seconds)
                    validation_is_running = False
                    return exit_code
                except subprocess.TimeoutExpired:
                    if rebuild_is_running(lock_directory):
                        print(
                            "operator rebuild started; restarting steward validation "
                            "after it finishes",
                            file=sys.stderr,
                            flush=True,
                        )
                        terminate_validation_process(validation_process)
                        validation_is_running = False
                        break
        finally:
            if validation_is_running:
                terminate_validation_process(validation_process)


def parse_arguments():
    parser = argparse.ArgumentParser(
        prog="steward-defer-to-rebuild",
        description="Wait for an active operator rebuild, then run a steward "
        "validation command at the lowest CPU and I/O priority.",
    )
    parser.add_argument(
        "--rebuild-lock-directory",
        type=Path,
        default=DEFAULT_REBUILD_LOCK_DIRECTORY,
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=DEFAULT_POLL_INTERVAL_SECONDS,
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    if arguments.command[:1] == ["--"]:
        arguments.command = arguments.command[1:]
    if not arguments.command:
        parser.error("a validation command is required after --")
    if arguments.poll_interval_seconds <= 0:
        parser.error("--poll-interval-seconds must be positive")
    return arguments


def main():
    arguments = parse_arguments()
    sys.exit(
        run_validation_with_rebuild_preemption(
            arguments.command,
            arguments.rebuild_lock_directory,
            arguments.poll_interval_seconds,
        )
    )


if __name__ == "__main__":
    main()
