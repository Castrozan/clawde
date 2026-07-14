import importlib.util
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)


def _load_agent_wrapper_module(module_name: str):
    if str(AGENT_WRAPPER_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))
    module_path = AGENT_WRAPPER_DIRECTORY / f"{module_name}.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


session_watchdog = _load_agent_wrapper_module("session_watchdog")


def test_stale_missing_session_line_in_scrollback_does_not_trigger_drop(monkeypatch):
    resumed_then_idle_pane_with_stale_crash_scrollback = (
        "No conversation found with session ID: old-crash-loop-session\n"
        "Agent could not resume its pinned session; dropping the stale session.\n"
        + "\n".join(f"resumed recap line {line_index}" for line_index in range(50))
        + "\n※ recap: continuing yesterday's migration work.\n"
        "● Heartbeat scheduled, nothing pending - standing by.\n❯\n"
    )
    monkeypatch.setattr(
        session_watchdog,
        "capture_pane_content",
        lambda _tmux_target: resumed_then_idle_pane_with_stale_crash_scrollback,
    )

    assert (
        session_watchdog.resume_launch_hit_missing_session(
            is_resume_launch=True,
            was_stuck_kill=False,
            tmux_target="clawde:ai-first-initiative",
        )
        is False
    )


def test_missing_session_line_in_pane_tail_still_triggers_drop(monkeypatch):
    genuinely_missing_resume_pane = (
        "\n".join(f"launch boot line {line_index}" for line_index in range(20))
        + "\nNo conversation found with session ID: pinned-but-never-persisted\n"
    )
    monkeypatch.setattr(
        session_watchdog,
        "capture_pane_content",
        lambda _tmux_target: genuinely_missing_resume_pane,
    )

    assert (
        session_watchdog.resume_launch_hit_missing_session(
            is_resume_launch=True,
            was_stuck_kill=False,
            tmux_target="clawde:ai-first-initiative",
        )
        is True
    )
