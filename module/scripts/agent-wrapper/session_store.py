import json
import os

SESSION_IDENTIFIER_SUBDIRECTORY = "session-ids"
REMEMBERED_PREVIOUS_SESSION_LIMIT = 10


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


def read_previous_session_identifiers(session_record_file_path: str) -> list[str]:
    try:
        with open(session_record_file_path) as session_record_file:
            persisted_record = json.load(session_record_file)
    except (OSError, ValueError):
        return []
    previous_session_identifiers = persisted_record.get("previous_session_identifiers")
    if not isinstance(previous_session_identifiers, list):
        return []
    return [
        identifier
        for identifier in previous_session_identifiers
        if isinstance(identifier, str) and identifier
    ]


def remember_previous_session_identifiers(
    retiring_session_identifier: str | None,
    previously_remembered_identifiers: list[str],
    current_session_identifier: str,
) -> list[str]:
    remembered_identifiers: list[str] = []
    for identifier in [retiring_session_identifier] + previously_remembered_identifiers:
        if not identifier or identifier == current_session_identifier:
            continue
        if identifier in remembered_identifiers:
            continue
        remembered_identifiers.append(identifier)
    return remembered_identifiers[:REMEMBERED_PREVIOUS_SESSION_LIMIT]


def write_persisted_session_record(
    session_record_file_path: str,
    session_identifier: str,
    started_on_date: str,
    previous_session_identifiers: list[str] | None = None,
) -> None:
    os.makedirs(os.path.dirname(session_record_file_path), exist_ok=True)
    temporary_file_path = f"{session_record_file_path}.{os.getpid()}.tmp"
    with open(temporary_file_path, "w") as session_record_file:
        json.dump(
            {
                "session_identifier": session_identifier,
                "started_on_date": started_on_date,
                "previous_session_identifiers": previous_session_identifiers or [],
            },
            session_record_file,
        )
    os.replace(temporary_file_path, session_record_file_path)


def clear_persisted_session_record(session_record_file_path: str) -> None:
    try:
        os.remove(session_record_file_path)
    except OSError:
        pass


def forget_session_identifier_from_record(
    session_record_file_path: str, session_identifier_to_forget: str
) -> None:
    persisted_session_identifier, started_on_date = read_persisted_session_record(
        session_record_file_path
    )
    surviving_previous_identifiers = [
        remembered_identifier
        for remembered_identifier in read_previous_session_identifiers(
            session_record_file_path
        )
        if remembered_identifier != session_identifier_to_forget
    ]
    surviving_session_identifier = (
        None
        if persisted_session_identifier == session_identifier_to_forget
        else persisted_session_identifier
    )
    if surviving_session_identifier is None and surviving_previous_identifiers:
        surviving_session_identifier = surviving_previous_identifiers.pop(0)
    if surviving_session_identifier is None:
        clear_persisted_session_record(session_record_file_path)
        return
    write_persisted_session_record(
        session_record_file_path,
        surviving_session_identifier,
        started_on_date,
        surviving_previous_identifiers,
    )
