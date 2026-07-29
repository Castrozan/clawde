import importlib.util
import pathlib
import re
import sys

from harness_profile_test_helpers import make_claude_profile, make_codex_profile

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
    session_argv, session_identifier = (
        session_identity.resolve_session_argv_and_identifier(
            make_claude_profile(), True, "abc-123"
        )
    )
    assert session_argv == "--resume abc-123"
    assert session_identifier == "abc-123"


def test_fresh_launch_pins_a_new_session_id_the_wrapper_can_later_resume():
    session_argv, session_identifier = (
        session_identity.resolve_session_argv_and_identifier(
            make_claude_profile(),
            False,
            None,
            session_identifier_generator=lambda: "fresh-uuid",
        )
    )
    assert session_argv == "--session-id fresh-uuid"
    assert session_identifier == "fresh-uuid"


def test_resume_request_without_a_known_session_falls_back_to_a_fresh_pinned_id():
    session_argv, session_identifier = (
        session_identity.resolve_session_argv_and_identifier(
            make_claude_profile(),
            True,
            None,
            session_identifier_generator=lambda: "fallback-uuid",
        )
    )
    assert session_argv == "--session-id fallback-uuid"
    assert session_identifier == "fallback-uuid"


def test_non_resume_launch_ignores_a_prior_session_and_pins_a_new_one():
    session_argv, session_identifier = (
        session_identity.resolve_session_argv_and_identifier(
            make_claude_profile(),
            False,
            "stale-session",
            session_identifier_generator=lambda: "rotated-uuid",
        )
    )
    assert session_argv == "--session-id rotated-uuid"
    assert session_identifier == "rotated-uuid"


def test_generated_session_identifier_is_a_valid_uuid():
    generated = session_identity.generate_session_identifier()
    assert re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        generated,
    )


def test_harness_owned_session_starts_bare_on_the_very_first_launch():
    session_argv, session_identifier = (
        session_identity.resolve_session_argv_and_identifier(
            make_codex_profile(), False, None
        )
    )
    assert session_argv == ""
    assert session_identifier == session_identity.HARNESS_OWNED_SESSION_MARKER


def test_harness_owned_session_reattaches_positionally_after_a_redeploy():
    session_argv, _ = session_identity.resolve_session_argv_and_identifier(
        make_codex_profile(),
        True,
        session_identity.HARNESS_OWNED_SESSION_MARKER,
    )
    assert session_argv == "resume --last"


def test_harness_owned_session_never_reattaches_before_a_session_exists():
    session_argv, _ = session_identity.resolve_session_argv_and_identifier(
        make_codex_profile(), True, None
    )
    assert session_argv == ""


def test_harness_owned_rotation_starts_fresh_rather_than_reattaching():
    session_argv, _ = session_identity.resolve_session_argv_and_identifier(
        make_codex_profile(),
        False,
        session_identity.HARNESS_OWNED_SESSION_MARKER,
    )
    assert session_argv == ""


def test_no_session_identifier_generator_is_consulted_for_a_harness_owned_session():
    def _fail_if_called():
        raise AssertionError(
            "clawde must not mint an identifier for a harness that owns session naming"
        )

    session_identity.resolve_session_argv_and_identifier(
        make_codex_profile(),
        False,
        None,
        session_identifier_generator=_fail_if_called,
    )
