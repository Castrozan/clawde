import time

from session_identity import resolve_resume_flag_and_session_identifier
from session_persistence import session_conversation_exists
from session_store import (
    build_session_record_file_path,
    read_persisted_session_record,
    read_previous_session_identifiers,
    remember_previous_session_identifiers,
    write_persisted_session_record,
)


class LaunchSessionDecision:
    def __init__(
        self,
        resume_flag: str,
        resume_previous_session: bool,
        rotating_session: bool,
        session_record_file_path: str,
        session_identifier: str,
    ) -> None:
        self.resume_flag = resume_flag
        self.resume_previous_session = resume_previous_session
        self.rotating_session = rotating_session
        self.session_record_file_path = session_record_file_path
        self.session_identifier = session_identifier


def resolve_resumable_session_identifier(
    persisted_session_identifier: str | None,
    previous_session_identifiers: list[str],
) -> str | None:
    for candidate_identifier in [
        persisted_session_identifier
    ] + previous_session_identifiers:
        if session_conversation_exists(candidate_identifier):
            return candidate_identifier
    return None


def decide_and_persist_launch_session(
    runtime_root_directory: str,
    agent_name: str,
    daily_session_rotation: bool,
) -> LaunchSessionDecision:
    session_record_file_path = build_session_record_file_path(
        runtime_root_directory, agent_name
    )
    persisted_session_identifier, persisted_started_on_date = (
        read_persisted_session_record(session_record_file_path)
    )
    previous_session_identifiers = read_previous_session_identifiers(
        session_record_file_path
    )
    today = time.strftime("%Y-%m-%d")

    rotating_session = (
        daily_session_rotation
        and persisted_started_on_date is not None
        and persisted_started_on_date != today
    )
    resumable_session_identifier = (
        None
        if rotating_session
        else resolve_resumable_session_identifier(
            persisted_session_identifier, previous_session_identifiers
        )
    )
    resume_previous_session = resumable_session_identifier is not None
    resume_flag, session_identifier = resolve_resume_flag_and_session_identifier(
        resume_previous_session, resumable_session_identifier
    )
    started_on_date = (
        persisted_started_on_date
        if resume_previous_session and persisted_started_on_date is not None
        else today
    )
    remembered_session_identifiers = [
        remembered_identifier
        for remembered_identifier in remember_previous_session_identifiers(
            persisted_session_identifier,
            previous_session_identifiers,
            session_identifier,
        )
        if session_conversation_exists(remembered_identifier)
    ]
    write_persisted_session_record(
        session_record_file_path,
        session_identifier,
        started_on_date,
        remembered_session_identifiers,
    )

    return LaunchSessionDecision(
        resume_flag=resume_flag,
        resume_previous_session=resume_previous_session,
        rotating_session=rotating_session,
        session_record_file_path=session_record_file_path,
        session_identifier=session_identifier,
    )
