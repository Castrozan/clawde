from agent_wrapper_test_support import (
    AGENT_DISCUSSING_AUTH_ERROR_THEN_IDLE_PANE,
    AUTH_FAILURE_MODAL_PANE,
    IDLE_REPL_PANE,
    USAGE_LIMIT_MODAL_PANE,
    load_agent_wrapper_module,
)
from harness_profile_test_helpers import make_claude_profile, make_codex_profile

stuck_indicators = load_agent_wrapper_module("stuck_indicators")
CLAUDE_PROFILE = make_claude_profile()

CODEX_IDLE_PANE = "• Standing by.\n  Ready · gpt-5.6-sol high · Context 3% used\n"
CODEX_WORKING_PANE = (
    "• Working on it.\n  Working · gpt-5.6-sol high · Context 3% used\n"
)


def _is_stuck(profile, current_pane, previous_pane):
    return stuck_indicators.pane_poll_is_stuck_evidence(
        profile, current_pane, previous_pane
    )


def test_idle_repl_pane_is_never_stuck_evidence_even_when_frozen():
    assert _is_stuck(CLAUDE_PROFILE, IDLE_REPL_PANE, IDLE_REPL_PANE) is False


def test_agent_discussing_auth_error_but_back_at_prompt_is_not_stuck():
    assert (
        _is_stuck(
            CLAUDE_PROFILE,
            AGENT_DISCUSSING_AUTH_ERROR_THEN_IDLE_PANE,
            AGENT_DISCUSSING_AUTH_ERROR_THEN_IDLE_PANE,
        )
        is False
    )


def test_progressing_pane_is_not_stuck_even_without_prompt():
    assert (
        _is_stuck(
            CLAUDE_PROFILE,
            "Running step 2 of 5... 41s\n",
            "Running step 2 of 5... 12s\n",
        )
        is False
    )


def test_frozen_non_idle_pane_is_stuck_evidence():
    assert (
        _is_stuck(CLAUDE_PROFILE, AUTH_FAILURE_MODAL_PANE, AUTH_FAILURE_MODAL_PANE)
        is True
    )


def test_first_poll_without_previous_capture_is_not_stuck_evidence():
    assert _is_stuck(CLAUDE_PROFILE, AUTH_FAILURE_MODAL_PANE, None) is False


def test_usage_limit_modal_is_stuck_evidence_on_first_sight():
    assert _is_stuck(CLAUDE_PROFILE, USAGE_LIMIT_MODAL_PANE, None) is True


def test_a_frozen_but_idle_codex_pane_is_not_stuck_evidence():
    assert _is_stuck(make_codex_profile(), CODEX_IDLE_PANE, CODEX_IDLE_PANE) is False


def test_a_frozen_working_codex_pane_is_stuck_evidence():
    assert (
        _is_stuck(make_codex_profile(), CODEX_WORKING_PANE, CODEX_WORKING_PANE) is True
    )


def test_a_codex_pane_is_not_judged_against_the_claude_prompt_marker():
    assert _is_stuck(CLAUDE_PROFILE, CODEX_IDLE_PANE, CODEX_IDLE_PANE) is True, (
        "reading a codex pane with the claude profile must not silently pass; the "
        "harness profile is what makes the idle verdict correct per harness"
    )
