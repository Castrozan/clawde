import json
import os

SESSION_IDENTIFIER_SUBDIRECTORY = "session-ids"


def build_session_record_file_path(runtime_root_directory: str, agent_name: str) -> str:
    return os.path.join(
        runtime_root_directory,
        SESSION_IDENTIFIER_SUBDIRECTORY,
        f"{agent_name}.json",
    )


def read_persisted_session_record(
    session_record_file_path: str,
) -> tuple[str | None, str | None]:
    try:
        with open(session_record_file_path) as session_record_file:
            persisted_record = json.load(session_record_file)
    except (OSError, ValueError):
        return (None, None)
    session_identifier = persisted_record.get("session_identifier")
    started_on_date = persisted_record.get("started_on_date")
    if not session_identifier:
        return (None, None)
    return (session_identifier, started_on_date)


def write_persisted_session_record(
    session_record_file_path: str, session_identifier: str, started_on_date: str
) -> None:
    os.makedirs(os.path.dirname(session_record_file_path), exist_ok=True)
    temporary_file_path = f"{session_record_file_path}.{os.getpid()}.tmp"
    with open(temporary_file_path, "w") as session_record_file:
        json.dump(
            {
                "session_identifier": session_identifier,
                "started_on_date": started_on_date,
            },
            session_record_file,
        )
    os.replace(temporary_file_path, session_record_file_path)


def clear_persisted_session_record(session_record_file_path: str) -> None:
    try:
        os.remove(session_record_file_path)
    except OSError:
        pass
