import re
import subprocess

AGENT_WRAPPER_PROCESS_MATCH_PATTERN = "agent-wrapper/wrapper.py --agent-name"
AGENT_NAME_PATTERN = re.compile(r"--agent-name (\S+)")
CONFIG_FILE_PATTERN = re.compile(r"--config-file (\S+)")


def find_agent_wrapper_process_ids() -> list[int]:
    completed_process = subprocess.run(
        ["pgrep", "-f", AGENT_WRAPPER_PROCESS_MATCH_PATTERN],
        capture_output=True,
        text=True,
    )
    return [
        int(line) for line in completed_process.stdout.split() if line.strip().isdigit()
    ]


def read_full_command_line(process_id: int) -> str:
    completed_process = subprocess.run(
        ["ps", "-ww", "-p", str(process_id), "-o", "command="],
        capture_output=True,
        text=True,
    )
    return completed_process.stdout.strip()


def parse_agent_wrapper_command_line(command_line: str) -> tuple[str, str] | None:
    agent_name_match = AGENT_NAME_PATTERN.search(command_line)
    config_file_match = CONFIG_FILE_PATTERN.search(command_line)
    if not agent_name_match or not config_file_match:
        return None
    return agent_name_match.group(1), config_file_match.group(1)


def find_wrapper_process_id_for_agent(agent_name: str) -> int | None:
    for process_id in find_agent_wrapper_process_ids():
        parsed_command_line = parse_agent_wrapper_command_line(
            read_full_command_line(process_id)
        )
        if parsed_command_line is not None and parsed_command_line[0] == agent_name:
            return process_id
    return None
