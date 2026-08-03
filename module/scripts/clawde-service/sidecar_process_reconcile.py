import os
import pathlib
import signal
import subprocess


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


def open_sidecar_log_file(log_file_path: str):
    log_file = pathlib.Path(log_file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    return log_file.open("a")


def detach_from_supervisor(command: str) -> str:
    return f"{{ {command} ; }} &"


def spawn_sidecar_process(sidecar_specification: dict) -> None:
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
