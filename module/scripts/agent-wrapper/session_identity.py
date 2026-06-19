import uuid


def generate_session_identifier() -> str:
    return str(uuid.uuid4())


def resolve_resume_flag_and_session_identifier(
    resume_requested: bool,
    current_session_identifier: str | None,
    session_identifier_generator=generate_session_identifier,
) -> tuple[str, str]:
    if resume_requested and current_session_identifier:
        return (
            f"--resume {current_session_identifier}",
            current_session_identifier,
        )
    fresh_session_identifier = session_identifier_generator()
    return (
        f"--session-id {fresh_session_identifier}",
        fresh_session_identifier,
    )
