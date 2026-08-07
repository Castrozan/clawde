from agent_wrapper_test_support import load_agent_wrapper_module
from harness_profile_test_helpers import make_opencode_profile

stuck_indicators = load_agent_wrapper_module("stuck_indicators")

OPENCODE_IDLE_PANE = """
  ┃
  ┃  Build · DeepSeek V4 Flash (2x usage) OpenCode Go · max
  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
   /home/agent/workspace                     tab agents  ctrl+p commands
"""

OPENCODE_WORKING_PANE = """
     ▣  Build · DeepSeek V4 Flash (2x usage)
  ┃
  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
   ⬝⬝⬝⬝⬝⬝⬝⬝  esc interrupt                  tab agents  ctrl+p commands
"""

OPENCODE_USAGE_LIMIT_RETRY_PANE = """
  ┃
  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
   ⬝⬝⬝⬝⬝⬝⬝⬝ weekly usage limit reached. It will reset in 2 days 10 hours. esc
                                                                       inte
                                                                       rrup
                                                                       t
"""

OPENCODE_USAGE_LIMIT_WRAPPED_MID_WORD_PANE = """
  ┃
  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
   ⬝⬝⬝⬝⬝⬝⬝⬝ weekly usage limit reac
                                   hed. It will reset in 2 days 10 hours.
                                   [retrying in ~2 days attempt #1]
"""


def test_idle_opencode_pane_is_recognized_at_prompt():
    assert make_opencode_profile().pane_is_at_idle_prompt(OPENCODE_IDLE_PANE)


def test_working_opencode_pane_is_not_idle():
    assert not make_opencode_profile().pane_is_at_idle_prompt(OPENCODE_WORKING_PANE)


def test_quota_exhausted_opencode_pane_is_read_as_a_usage_limit():
    assert make_opencode_profile().pane_indicates_usage_limit_modal(
        OPENCODE_USAGE_LIMIT_RETRY_PANE
    ), (
        "opencode parks a quota-exhausted agent on a retry banner for days, so the "
        "wording it actually renders has to count as a usage limit or the agent looks "
        "supervised while doing nothing"
    )


def test_a_usage_limit_banner_wrapped_mid_word_is_still_read_as_a_usage_limit():
    assert make_opencode_profile().pane_indicates_usage_limit_modal(
        OPENCODE_USAGE_LIMIT_WRAPPED_MID_WORD_PANE
    ), (
        "the status row wraps mid-word at narrow pane widths, so a plain substring "
        "search over the raw capture misses the banner it is meant to catch"
    )


def test_an_idle_opencode_pane_is_not_a_usage_limit():
    assert not make_opencode_profile().pane_indicates_usage_limit_modal(
        OPENCODE_IDLE_PANE
    )


def test_quota_exhausted_opencode_pane_is_stuck_evidence_for_the_watchdog():
    assert (
        stuck_indicators.pane_poll_is_stuck_evidence(
            make_opencode_profile(),
            OPENCODE_USAGE_LIMIT_RETRY_PANE,
            OPENCODE_USAGE_LIMIT_RETRY_PANE,
        )
        is True
    )
