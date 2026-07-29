import json

import pytest
from harness_profile_test_helpers import (
    CODEX_PROFILE_MAPPING,
    make_claude_profile,
    make_codex_profile,
)
from harness_runtime_profile import (
    load_harness_runtime_profile_from_launch_config,
)

CODEX_IDLE_PANE = """
› Run /review on my current changes
  Ready · gpt-5.6-sol high · Context 4% used
"""

CODEX_WORKING_PANE = """
• Running it now.
Working (0s • esc to interrupt) · 1 background terminal running
› Run /review on my current changes
  Working · gpt-5.6-sol high · Context 4% used
"""

CODEX_TRUST_MODAL_PANE = """
> You are in /home/agent/workspace
  Do you trust the contents of this directory? Working with untrusted contents comes
› 1. Yes, continue
  2. No, quit
"""

CLAUDE_IDLE_PANE = """
⏺ Done.

 ❯
"""

CLAUDE_WORKING_PANE = """
⏺ Thinking...

  Running (esc to interrupt)
"""


def test_codex_idle_pane_is_recognized_at_prompt():
    assert make_codex_profile().pane_is_at_idle_prompt(CODEX_IDLE_PANE)


def test_codex_working_pane_is_not_idle():
    assert not make_codex_profile().pane_is_at_idle_prompt(CODEX_WORKING_PANE)


def test_claude_idle_pane_is_recognized_at_prompt():
    assert make_claude_profile().pane_is_at_idle_prompt(CLAUDE_IDLE_PANE)


def test_claude_working_pane_is_not_idle():
    assert not make_claude_profile().pane_is_at_idle_prompt(CLAUDE_WORKING_PANE)


def test_a_harness_does_not_match_another_harness_idle_marker():
    assert not make_claude_profile().pane_is_at_idle_prompt(CODEX_IDLE_PANE)
    assert not make_codex_profile().pane_is_at_idle_prompt(CLAUDE_IDLE_PANE)


def test_codex_trust_modal_suppresses_the_idle_verdict():
    profile = make_codex_profile()
    assert profile.pane_is_at_onboarding(CODEX_TRUST_MODAL_PANE)
    assert not profile.pane_is_at_idle_prompt(CODEX_TRUST_MODAL_PANE)


def test_codex_trust_modal_is_dismissable_with_its_declared_key():
    modal = make_codex_profile().matching_pre_prompt_modal(CODEX_TRUST_MODAL_PANE)
    assert modal is not None
    assert modal["dismiss_key"] == "Enter"


def test_no_modal_matches_an_idle_pane():
    assert make_codex_profile().matching_pre_prompt_modal(CODEX_IDLE_PANE) is None


def test_claude_resume_modal_needs_every_indicator_present():
    full_modal = (
        "Resuming the full session will consume 45,000 tokens.\n"
        " ❯ Resume full session as-is\n"
    )
    assert make_claude_profile().matching_pre_prompt_modal(full_modal) is not None


def test_a_single_resume_modal_indicator_alone_is_not_the_modal():
    only_the_headline = "Resuming the full session will consume 45,000 tokens.\n❯\n"
    assert make_claude_profile().matching_pre_prompt_modal(only_the_headline) is None, (
        "the confirmation modal is only present when every indicator line is on "
        "screen, so a stray headline in scrollback must not be read as a live modal"
    )


def test_missing_resume_session_is_detected_from_the_cli_error():
    error_pane = "No conversation found with session ID: 1c0ffee5-dead-beef\n"
    assert make_claude_profile().pane_indicates_missing_resume_session(error_pane)


def test_idle_pane_is_not_a_missing_resume_session():
    assert not make_claude_profile().pane_indicates_missing_resume_session(
        CLAUDE_IDLE_PANE
    )


def test_a_harness_without_a_transcript_store_declares_so():
    assert make_claude_profile().exposes_session_transcript_store()
    assert not make_codex_profile().exposes_session_transcript_store()


def test_claude_renders_an_explicit_identifier_into_both_session_templates():
    profile = make_claude_profile()
    assert (
        profile.render_session_argv("abc-123", resuming=False) == "--session-id abc-123"
    )
    assert profile.render_session_argv("abc-123", resuming=True) == "--resume abc-123"


def test_codex_starts_bare_and_reattaches_positionally():
    profile = make_codex_profile()
    assert profile.render_session_argv(None, resuming=False) == ""
    assert profile.render_session_argv(None, resuming=True) == "resume --last"


@pytest.mark.parametrize(
    "pane, expected",
    [
        ("Wait for limit to reset", False),
        ("You've hit your usage limit", True),
    ],
)
def test_usage_limit_indicators_do_not_leak_across_harnesses(pane, expected):
    assert make_codex_profile().pane_indicates_usage_limit_modal(pane) is expected


def test_profile_loads_from_an_agent_launch_config(tmp_path):
    launch_config_path = tmp_path / "agent.json"
    launch_config_path.write_text(
        json.dumps(
            {
                "launch_command": "codex",
                "harness_runtime_profile": CODEX_PROFILE_MAPPING,
            }
        )
    )
    profile = load_harness_runtime_profile_from_launch_config(str(launch_config_path))
    assert profile.harness_name == "codex"
    assert profile.live_process_name_fragment == "codex"
    assert not profile.generates_session_identifier
