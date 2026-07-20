import os
from pathlib import Path


def claude_projects_root() -> Path:
    return Path(os.path.expanduser("~/.claude/projects"))


def claude_project_directory_for_workspace(workspace_directory: str) -> Path:
    return claude_projects_root() / str(workspace_directory).replace("/", "-")


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
