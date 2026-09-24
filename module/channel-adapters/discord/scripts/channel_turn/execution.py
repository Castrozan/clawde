import os
import subprocess
import tempfile
import time
from pathlib import Path

from channel_turn import session
from channel_turn.result import ChannelTurnResult, completed_channel_turn

TURN_TIMEOUT_SECONDS = 900


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


def run_one_turn(
    one_shot_turn_command: str,
    workspace_directory: str,
    state_directory: str,
    prompt: str,
    daily_session_rotation: bool = False,
) -> ChannelTurnResult:
    session.rotate_the_channel_session_if_needed(
        state_directory, daily_session_rotation
    )
    session_identifier = session.read_channel_session_identifier(state_directory)
    resuming = (
        session.a_previous_turn_is_resumable(state_directory)
        and session_identifier is not None
    )
    if not resuming:
        session_identifier = session.mint_fresh_channel_session_identifier(
            state_directory
        )
    with tempfile.TemporaryDirectory() as reply_directory:
        reply_file_path = os.path.join(reply_directory, "reply.txt")
        try:
            completed_turn = subprocess.run(
                ["bash", "-o", "pipefail", "-c", one_shot_turn_command],
                cwd=workspace_directory,
                env=build_turn_environment(
                    prompt, reply_file_path, resuming, session_identifier
                ),
                capture_output=True,
                text=True,
                timeout=TURN_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            session.forget_the_channel_session(state_directory)
            return ChannelTurnResult(
                failure=f"one-shot turn exceeded {TURN_TIMEOUT_SECONDS} seconds"
            )
        except OSError as error:
            session.forget_the_channel_session(state_directory)
            return ChannelTurnResult(failure=f"could not start one-shot turn: {error}")
        if completed_turn.returncode != 0:
            session.forget_the_channel_session(state_directory)
            return ChannelTurnResult(
                failure=completed_turn.stderr.strip()
                or f"one-shot turn exited with status {completed_turn.returncode}"
            )
        try:
            reply = Path(reply_file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            session.forget_the_channel_session(state_directory)
            return ChannelTurnResult(
                failure=f"one-shot turn did not publish a readable reply result: {error}"
            )
    session.remember_that_a_turn_completed(state_directory)
    session.write_channel_session_last_turn_date(
        state_directory, time.strftime("%Y-%m-%d")
    )
    return completed_channel_turn(reply)
