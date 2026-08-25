import argparse
import os
import subprocess

SUPERVISOR_PROCESS_MATCH_PATTERN = "clawde-service.py --specification-file"


def inspect_processes(command: list[str]) -> str:
    try:
        return subprocess.run(command, capture_output=True, text=True).stdout
    except OSError:
        return ""


def find_supervisor_process_ids() -> list[int]:
    own_process_id = os.getpid()
    return [
        int(line)
        for line in inspect_processes(
            ["pgrep", "-f", SUPERVISOR_PROCESS_MATCH_PATTERN]
        ).split()
        if line.strip().isdigit() and int(line) != own_process_id
    ]


def read_full_command_line(process_id: int) -> str:
    return inspect_processes(
        ["ps", "-ww", "-o", "command=", "-p", str(process_id)]
    ).strip()


def read_deployed_command(deployed_command_file: str) -> str:
    with open(deployed_command_file) as command_file:
        return command_file.read().strip()


def supervisor_runs_superseded_code(deployed_command: str) -> bool:
    for process_id in find_supervisor_process_ids():
        command_line = read_full_command_line(process_id)
        if command_line and command_line != deployed_command:
            return True
    return False


def restart_the_supervisor(restart_command: str) -> int:
    return subprocess.run(["sh", "-c", restart_command]).returncode


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-supervisor-refresh",
        description="Restart the clawde supervisor when the code it is running is "
        "no longer the code this generation deploys. The unit is marked "
        "X-RestartIfChanged=false so a rebuild never disturbs a healthy supervisor, "
        "which also means new supervisor code would otherwise stay dormant until "
        "someone restarted it by hand.",
    )
    parser.add_argument("--deployed-command-file", required=True)
    parser.add_argument("--restart-command", required=True)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    deployed_command = read_deployed_command(arguments.deployed_command_file)
    if not supervisor_runs_superseded_code(deployed_command):
        print("clawde supervisor already runs this generation's code.")
        return 0
    print("clawde supervisor runs superseded code; restarting it.")
    return restart_the_supervisor(arguments.restart_command)


if __name__ == "__main__":
    raise SystemExit(main())
