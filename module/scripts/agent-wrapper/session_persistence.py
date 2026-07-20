import datetime
import os
import re
from pathlib import Path

NON_ALPHANUMERIC_CHARACTER = re.compile(r"[^a-zA-Z0-9]")


def claude_projects_root() -> Path:
    return Path(os.path.expanduser("~/.claude/projects"))


def claude_project_directory_for_workspace(workspace_directory: str) -> Path:
    return claude_projects_root() / NON_ALPHANUMERIC_CHARACTER.sub(
        "-", str(workspace_directory)
    )


def session_conversation_file(
    session_identifier: str, workspace_directory: str
) -> Path:
    return (
        claude_project_directory_for_workspace(workspace_directory)
        / f"{session_identifier}.jsonl"
    )


def session_conversation_exists(
    session_identifier: str | None, workspace_directory: str | None = None
) -> bool:
    if not session_identifier:
        return False
    if workspace_directory is None:
        workspace_directory = os.getcwd()
    return session_conversation_file(session_identifier, workspace_directory).is_file()


def session_conversation_modified_at(
    session_identifier: str | None, workspace_directory: str | None
) -> datetime.datetime | None:
    if not session_identifier or not workspace_directory:
        return None
    conversation_file = session_conversation_file(
        session_identifier, workspace_directory
    )
    try:
        return datetime.datetime.fromtimestamp(conversation_file.stat().st_mtime)
    except OSError:
        return None
