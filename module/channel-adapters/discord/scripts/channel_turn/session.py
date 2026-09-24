import os
import time
import uuid

SESSION_STARTED_MARKER_FILE_NAME = "bridge-session-started"
CHANNEL_SESSION_IDENTIFIER_FILE_NAME = "channel-session-identifier"
CHANNEL_SESSION_LAST_TURN_DATE_FILE_NAME = "channel-session-last-turn-date"


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
