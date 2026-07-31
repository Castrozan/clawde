import os
import subprocess
import tempfile

SESSION_STARTED_MARKER_FILE_NAME = "bridge-session-started"
TURN_TIMEOUT_SECONDS = 900


def session_started_marker_path(state_directory: str) -> str:
    return os.path.join(state_directory, SESSION_STARTED_MARKER_FILE_NAME)


def a_previous_turn_is_resumable(state_directory: str) -> bool:
    return os.path.isfile(session_started_marker_path(state_directory))


def remember_that_a_turn_completed(state_directory: str) -> None:
    os.makedirs(state_directory, exist_ok=True)
    with open(session_started_marker_path(state_directory), "w") as marker_file:
        marker_file.write("")


def forget_the_previous_turn(state_directory: str) -> None:
    try:
        os.remove(session_started_marker_path(state_directory))
    except FileNotFoundError:
        pass


def build_turn_environment(
    prompt: str, reply_file_path: str, resuming: bool
) -> dict[str, str]:
    return {
        **os.environ,
        "CLAWDE_CHANNEL_PROMPT": prompt,
        "CLAWDE_CHANNEL_REPLY_FILE": reply_file_path,
        "CLAWDE_CHANNEL_SESSION_CONTINUATION": "1" if resuming else "",
    }


def read_reply_file(reply_file_path: str) -> str:
    try:
        with open(reply_file_path) as reply_file:
            return reply_file.read().strip()
    except OSError:
        return ""


def run_one_turn(
    one_shot_turn_command: str,
    workspace_directory: str,
    state_directory: str,
    prompt: str,
) -> tuple[str, str]:
    resuming = a_previous_turn_is_resumable(state_directory)
    with tempfile.TemporaryDirectory() as reply_directory:
        reply_file_path = os.path.join(reply_directory, "reply.txt")
        completed_turn = subprocess.run(
            ["bash", "-c", one_shot_turn_command],
            cwd=workspace_directory,
            env=build_turn_environment(prompt, reply_file_path, resuming),
            capture_output=True,
            text=True,
            timeout=TURN_TIMEOUT_SECONDS,
        )
        reply = read_reply_file(reply_file_path)
    if reply:
        remember_that_a_turn_completed(state_directory)
        return reply, ""
    if resuming:
        forget_the_previous_turn(state_directory)
    return "", (completed_turn.stderr or completed_turn.stdout).strip()
