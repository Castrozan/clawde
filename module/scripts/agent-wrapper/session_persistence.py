import datetime
import os
from pathlib import Path


def session_transcript_file(
    harness_runtime_profile,
    session_identifier: str,
    workspace_directory: str,
) -> Path:
    return Path(
        harness_runtime_profile.render_session_transcript_path(
            session_identifier, workspace_directory
        )
    )


def session_conversation_exists(
    harness_runtime_profile,
    session_identifier: str | None,
    workspace_directory: str | None = None,
) -> bool:
    if not session_identifier:
        return False
    if not harness_runtime_profile.exposes_session_transcript_store():
        return True
    if workspace_directory is None:
        workspace_directory = os.getcwd()
    return session_transcript_file(
        harness_runtime_profile, session_identifier, workspace_directory
    ).is_file()


def session_conversation_modified_at(
    harness_runtime_profile,
    session_identifier: str | None,
    workspace_directory: str | None,
) -> datetime.datetime | None:
    if not session_identifier or not workspace_directory:
        return None
    if not harness_runtime_profile.exposes_session_transcript_store():
        return None
    transcript_file = session_transcript_file(
        harness_runtime_profile, session_identifier, workspace_directory
    )
    try:
        return datetime.datetime.fromtimestamp(transcript_file.stat().st_mtime)
    except OSError:
        return None
