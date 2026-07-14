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

IDLE_REPL_PANE = "● Heartbeat scheduled, nothing pending - standing by.\n❯\n"
RESUME_CONFIRMATION_MODAL_PANE = (
    "Resuming the full session will consume 45,000 tokens.\n"
    " ❯ Resume full session as-is\n"
    "   Summarize the session first, then resume\n"
)


def test_resume_launch_dismisses_the_resume_confirmation_modal_then_stops(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    captures_before_the_modal_clears = [RESUME_CONFIRMATION_MODAL_PANE]

    def capture_modal_then_idle(_tmux_target):
        if captures_before_the_modal_clears:
            return captures_before_the_modal_clears.pop(0)
        return IDLE_REPL_PANE

    monkeypatch.setattr(
        session_watchdog, "capture_pane_content", capture_modal_then_idle
    )
    enter_key_sends = []

    def record_enter_key(tmux_target):
        enter_key_sends.append(tmux_target)
        return True

    monkeypatch.setattr(session_watchdog, "send_enter_key_to_pane", record_enter_key)

    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 0.3",
            None,
            "clawde:ai-first-initiative",
            resume_flag="--resume pinned-session-id",
            is_resume_launch=True,
        )
    )
    assert enter_key_sends == ["clawde:ai-first-initiative"], (
        "a no-heartbeat agent resuming a large session hits the resume-confirmation "
        "modal; the wrapper must press Enter once to dismiss it, then disarm the moment "
        "the pane returns to the idle REPL prompt instead of pressing forever"
    )
    assert was_stuck_kill is False


def test_resume_modal_watch_disarms_after_the_bounded_poll_budget(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog,
        "capture_pane_content",
        lambda _tmux_target: RESUME_CONFIRMATION_MODAL_PANE,
    )
    enter_key_sends = []
    monkeypatch.setattr(
        session_watchdog,
        "send_enter_key_to_pane",
        lambda tmux_target: enter_key_sends.append(tmux_target) or True,
    )

    def terminate_and_kill(root_process_id):
        session_watchdog.os.kill(root_process_id, session_watchdog.signal.SIGKILL)

    monkeypatch.setattr(session_watchdog, "terminate_process_tree", terminate_and_kill)

    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 30",
            None,
            "clawde:ai-first-initiative",
            resume_flag="--resume pinned-session-id",
            is_resume_launch=True,
        )
    )
    assert len(enter_key_sends) <= session_watchdog.RESUME_MODAL_WATCH_MAX_POLLS, (
        "if the modal never clears the wrapper must stop pressing Enter after a bounded "
        "budget so it cannot spam Enter into a pane that is genuinely wedged"
    )
    assert was_stuck_kill is True, (
        "once the modal watch disarms, a pane frozen on a non-idle modal is stuck "
        "evidence and the watchdog must kill it into a fresh restart"
    )


def test_non_resume_launch_never_presses_enter_into_the_pane(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog,
        "capture_pane_content",
        lambda _tmux_target: RESUME_CONFIRMATION_MODAL_PANE,
    )
    enter_key_sends = []
    monkeypatch.setattr(
        session_watchdog,
        "send_enter_key_to_pane",
        lambda tmux_target: enter_key_sends.append(tmux_target) or True,
    )

    def terminate_and_kill(root_process_id):
        session_watchdog.os.kill(root_process_id, session_watchdog.signal.SIGKILL)

    monkeypatch.setattr(session_watchdog, "terminate_process_tree", terminate_and_kill)

    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 30",
            None,
            "clawde:golden",
            is_resume_launch=False,
        )
    )
    assert enter_key_sends == [], (
        "a fresh (non-resume) launch never faces the resume modal; the wrapper must "
        "not inject Enter into the pane where it could land inside the agent's work"
    )
    assert was_stuck_kill is True
