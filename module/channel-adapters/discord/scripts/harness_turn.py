import os
import subprocess
import tempfile
import time
import uuid

SESSION_STARTED_MARKER_FILE_NAME = "bridge-session-started"
CHANNEL_SESSION_IDENTIFIER_FILE_NAME = "channel-session-identifier"
CHANNEL_SESSION_LAST_TURN_DATE_FILE_NAME = "channel-session-last-turn-date"
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


def channel_session_identifier_path(state_directory: str) -> str:
    return os.path.join(state_directory, CHANNEL_SESSION_IDENTIFIER_FILE_NAME)


def read_channel_session_identifier(state_directory: str) -> str | None:
    try:
        with open(channel_session_identifier_path(state_directory)) as identifier_file:
            identifier = identifier_file.read().strip()
    except OSError:
        return None
    return identifier or None


def write_channel_session_identifier(state_directory: str, identifier: str) -> None:
    os.makedirs(state_directory, exist_ok=True)
    with open(channel_session_identifier_path(state_directory), "w") as identifier_file:
        identifier_file.write(identifier)


def mint_fresh_channel_session_identifier(state_directory: str) -> str:
    identifier = str(uuid.uuid4())
    write_channel_session_identifier(state_directory, identifier)
    return identifier


def forget_the_channel_session(state_directory: str) -> None:
    forget_the_previous_turn(state_directory)
    try:
        os.remove(channel_session_identifier_path(state_directory))
    except FileNotFoundError:
        pass


def channel_session_last_turn_date_path(state_directory: str) -> str:
    return os.path.join(state_directory, CHANNEL_SESSION_LAST_TURN_DATE_FILE_NAME)


def read_channel_session_last_turn_date(state_directory: str) -> str | None:
    try:
        with open(channel_session_last_turn_date_path(state_directory)) as date_file:
            last_turn_date = date_file.read().strip()
    except OSError:
        return None
    return last_turn_date or None


def write_channel_session_last_turn_date(state_directory: str, date: str) -> None:
    os.makedirs(state_directory, exist_ok=True)
    with open(channel_session_last_turn_date_path(state_directory), "w") as date_file:
        date_file.write(date)


def channel_session_crossed_a_rotation_boundary(
    state_directory: str, daily_session_rotation: bool, today: str
) -> bool:
    if not daily_session_rotation:
        return False
    last_turn_date = read_channel_session_last_turn_date(state_directory)
    return last_turn_date is not None and last_turn_date != today


def rotate_the_channel_session_if_needed(
    state_directory: str, daily_session_rotation: bool
) -> None:
    if channel_session_crossed_a_rotation_boundary(
        state_directory, daily_session_rotation, time.strftime("%Y-%m-%d")
    ):
        forget_the_channel_session(state_directory)


def build_turn_environment(
    prompt: str, reply_file_path: str, resuming: bool, session_identifier: str
) -> dict[str, str]:
    return {
        **os.environ,
        "CLAWDE_CHANNEL_PROMPT": prompt,
        "CLAWDE_CHANNEL_REPLY_FILE": reply_file_path,
        "CLAWDE_CHANNEL_SESSION_CONTINUATION": "1" if resuming else "",
        "CLAWDE_CHANNEL_SESSION_IDENTIFIER": session_identifier,
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
    daily_session_rotation: bool = False,
) -> tuple[str, str]:
    rotate_the_channel_session_if_needed(state_directory, daily_session_rotation)
    resuming = (
        a_previous_turn_is_resumable(state_directory)
        and read_channel_session_identifier(state_directory) is not None
    )
    if resuming:
        session_identifier = read_channel_session_identifier(state_directory)
        assert session_identifier is not None
    else:
        session_identifier = mint_fresh_channel_session_identifier(state_directory)
    with tempfile.TemporaryDirectory() as reply_directory:
        reply_file_path = os.path.join(reply_directory, "reply.txt")
        completed_turn = subprocess.run(
            ["bash", "-c", one_shot_turn_command],
            cwd=workspace_directory,
            env=build_turn_environment(
                prompt, reply_file_path, resuming, session_identifier
            ),
            capture_output=True,
            text=True,
            timeout=TURN_TIMEOUT_SECONDS,
        )
        reply = read_reply_file(reply_file_path)
    if reply:
        remember_that_a_turn_completed(state_directory)
        write_channel_session_last_turn_date(state_directory, time.strftime("%Y-%m-%d"))
        return reply, ""
    forget_the_channel_session(state_directory)
    return "", (completed_turn.stderr or completed_turn.stdout).strip()
