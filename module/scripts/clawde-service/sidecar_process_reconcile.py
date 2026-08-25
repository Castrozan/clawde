import os
import pathlib
import signal
import subprocess
import time

SPAWNED_COMMAND_RECORD_SUFFIX = ".spawned-command"
TERMINATION_DEADLINE_SECONDS = 5.0
TERMINATION_POLL_SECONDS = 0.1


def find_sidecar_process_ids(process_match_pattern: str) -> list[int]:
    pgrep_result = subprocess.run(
        ["pgrep", "-f", process_match_pattern],
        capture_output=True,
        text=True,
    )
    return [int(line) for line in pgrep_result.stdout.split() if line.strip().isdigit()]


def terminate_sidecar_process(process_id: int) -> None:
    try:
        os.kill(process_id, signal.SIGTERM)
    except ProcessLookupError:
        pass


def process_is_alive(process_id: int) -> bool:
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    return True


def termination_poll_attempts() -> int:
    return int(TERMINATION_DEADLINE_SECONDS / TERMINATION_POLL_SECONDS)


def wait_for_process_to_exit(process_id: int) -> None:
    for _attempt in range(termination_poll_attempts()):
        if not process_is_alive(process_id):
            return
        time.sleep(TERMINATION_POLL_SECONDS)


def spawned_command_record_for(sidecar_specification: dict) -> pathlib.Path:
    return pathlib.Path(
        sidecar_specification["log_file"] + SPAWNED_COMMAND_RECORD_SUFFIX
    )


def recorded_spawned_command(sidecar_specification: dict) -> str | None:
    record_file = spawned_command_record_for(sidecar_specification)
    try:
        return record_file.read_text()
    except OSError:
        return None


def record_spawned_command(sidecar_specification: dict) -> None:
    record_file = spawned_command_record_for(sidecar_specification)
    record_file.parent.mkdir(parents=True, exist_ok=True)
    record_file.write_text(sidecar_specification["command"])


def live_processes_run_the_current_command(sidecar_specification: dict) -> bool:
    return (
        recorded_spawned_command(sidecar_specification)
        == (sidecar_specification["command"])
    )


def replace_processes_running_superseded_code(
    sidecar_specification: dict, live_process_ids: list[int]
) -> list[int]:
    if not live_process_ids or live_processes_run_the_current_command(
        sidecar_specification
    ):
        return live_process_ids
    for process_id in live_process_ids:
        terminate_sidecar_process(process_id)
    for process_id in live_process_ids:
        wait_for_process_to_exit(process_id)
    return []


def open_sidecar_log_file(log_file_path: str):
    log_file = pathlib.Path(log_file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    return log_file.open("a")


def detach_from_supervisor(command: str) -> str:
    return f"{{ {command} ; }} &"


def spawn_sidecar_process(sidecar_specification: dict) -> None:
    record_spawned_command(sidecar_specification)
    with open_sidecar_log_file(sidecar_specification["log_file"]) as log_file:
        subprocess.run(
            ["sh", "-c", detach_from_supervisor(sidecar_specification["command"])],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )


def reconcile_one_sidecar_process(
    sidecar_specification: dict, sidecar_should_be_running: bool
) -> bool:
    live_process_ids = sorted(
        find_sidecar_process_ids(sidecar_specification["process_match_pattern"])
    )
    if not sidecar_should_be_running:
        for process_id in live_process_ids:
            terminate_sidecar_process(process_id)
        return False
    live_process_ids = replace_processes_running_superseded_code(
        sidecar_specification, live_process_ids
    )
    for duplicate_process_id in live_process_ids[1:]:
        terminate_sidecar_process(duplicate_process_id)
    if live_process_ids:
        return False
    spawn_sidecar_process(sidecar_specification)
    return True


def reconcile_sidecar_processes_for_session(
    session_specification: dict, agent_names_that_should_be_running: set
) -> None:
    for agent_specification in session_specification["agents"]:
        agent_name = agent_specification["name"]
        for sidecar_specification in agent_specification.get("sidecar_processes", []):
            sidecar_should_be_running = sidecar_should_be_running_for(
                agent_name,
                sidecar_specification,
                agent_names_that_should_be_running,
            )
            reconcile_one_sidecar_process(
                sidecar_specification, sidecar_should_be_running
            )


def sidecar_should_be_running_for(
    agent_name: str,
    sidecar_specification: dict,
    agent_names_that_should_be_running: set,
) -> bool:
    if not sidecar_specification.get("enabled", True):
        return False
    if sidecar_specification.get("lifetime", "agent") == "service":
        return True
    return agent_name in agent_names_that_should_be_running
