import datetime
import glob
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


def workspace_transcript_files(
    harness_runtime_profile, workspace_directory: str
) -> list[str]:
    return glob.glob(
        os.path.join(
            harness_runtime_profile.render_session_transcript_directory(
                workspace_directory
            ),
            harness_runtime_profile.render_session_transcript_file_name_glob(),
        )
    )


def latest_workspace_conversation_modified_at(
    harness_runtime_profile,
    workspace_directory: str | None,
) -> datetime.datetime | None:
    if not workspace_directory:
        return None
    if not harness_runtime_profile.exposes_session_transcript_store():
        return None
    modification_times = []
    for transcript_file_path in workspace_transcript_files(
        harness_runtime_profile, workspace_directory
    ):
        try:
            modification_times.append(os.stat(transcript_file_path).st_mtime)
        except OSError:
            continue
    if not modification_times:
        return None
    return datetime.datetime.fromtimestamp(max(modification_times))
