import uuid

HARNESS_OWNED_SESSION_MARKER = "harness-owned-session"


def generate_session_identifier() -> str:
    return str(uuid.uuid4())


def resolve_session_argv_and_identifier(
    harness_runtime_profile,
    resume_previous_session: bool,
    resumable_session_identifier: str | None,
    session_identifier_generator=generate_session_identifier,
) -> tuple[str, str]:
    if not harness_runtime_profile.generates_session_identifier:
        reattaching = (
            resume_previous_session and resumable_session_identifier is not None
        )
        return (
            harness_runtime_profile.render_session_argv(None, resuming=reattaching),
            HARNESS_OWNED_SESSION_MARKER,
        )

    if resume_previous_session and resumable_session_identifier:
        return (
            harness_runtime_profile.render_session_argv(
                resumable_session_identifier, resuming=True
            ),
            resumable_session_identifier,
        )

    fresh_session_identifier = session_identifier_generator()
    return (
        harness_runtime_profile.render_session_argv(
            fresh_session_identifier, resuming=False
        ),
        fresh_session_identifier,
    )
