import importlib.util
import pathlib
import re
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)


def _load_session_identity_module():
    if str(AGENT_WRAPPER_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))
    module_path = AGENT_WRAPPER_DIRECTORY / "session_identity.py"
    module_spec = importlib.util.spec_from_file_location(
        "session_identity", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


session_identity = _load_session_identity_module()


def test_resume_request_with_a_known_session_resumes_that_exact_session():
    resume_flag, session_identifier = (
        session_identity.resolve_resume_flag_and_session_identifier(True, "abc-123")
    )
    assert resume_flag == "--resume abc-123"
    assert session_identifier == "abc-123"


def test_fresh_launch_pins_a_new_session_id_the_wrapper_can_later_resume():
    resume_flag, session_identifier = (
        session_identity.resolve_resume_flag_and_session_identifier(
            False, None, session_identifier_generator=lambda: "fresh-uuid"
        )
    )
    assert resume_flag == "--session-id fresh-uuid"
    assert session_identifier == "fresh-uuid"


def test_resume_request_without_a_known_session_falls_back_to_a_fresh_pinned_id():
    resume_flag, session_identifier = (
        session_identity.resolve_resume_flag_and_session_identifier(
            True, None, session_identifier_generator=lambda: "fallback-uuid"
        )
    )
    assert resume_flag == "--session-id fallback-uuid"
    assert session_identifier == "fallback-uuid"


def test_non_resume_launch_ignores_a_prior_session_and_pins_a_new_one():
    resume_flag, session_identifier = (
        session_identity.resolve_resume_flag_and_session_identifier(
            False,
            "stale-session",
            session_identifier_generator=lambda: "rotated-uuid",
        )
    )
    assert resume_flag == "--session-id rotated-uuid"
    assert session_identifier == "rotated-uuid"


def test_generated_session_identifier_is_a_valid_uuid():
    generated = session_identity.generate_session_identifier()
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        generated,
    )
