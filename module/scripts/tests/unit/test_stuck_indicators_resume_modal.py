import importlib.util
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)


def _load_stuck_indicators_module():
    if str(AGENT_WRAPPER_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))
    module_path = AGENT_WRAPPER_DIRECTORY / "stuck_indicators.py"
    module_spec = importlib.util.spec_from_file_location(
        "stuck_indicators", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


stuck_indicators = _load_stuck_indicators_module()


def test_resume_modal_needs_every_indicator_present():
    full_modal = (
        "Resuming the full session will consume 45,000 tokens.\n"
        " ❯ Resume full session as-is\n"
    )
    assert stuck_indicators.pane_indicates_resume_confirmation_modal(full_modal) is True


def test_a_single_resume_modal_indicator_alone_is_not_the_modal():
    only_the_headline = "Resuming the full session will consume 45,000 tokens.\n❯\n"
    assert (
        stuck_indicators.pane_indicates_resume_confirmation_modal(only_the_headline)
        is False
    ), (
        "the confirmation modal is only present when every indicator line is on screen, "
        "so a stray headline in scrollback must not be read as a live modal"
    )


def test_missing_resume_session_is_detected_from_the_cli_error():
    error_pane = "No conversation found with session ID: 1c0ffee5-dead-beef\n"
    assert stuck_indicators.pane_indicates_missing_resume_session(error_pane) is True


def test_idle_pane_is_not_a_missing_resume_session():
    idle_pane = "● Heartbeat scheduled, nothing pending - standing by.\n❯\n"
    assert stuck_indicators.pane_indicates_missing_resume_session(idle_pane) is False
