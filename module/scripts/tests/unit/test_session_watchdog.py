import importlib.util
import pathlib
import sys

from harness_profile_test_helpers import make_claude_profile

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

CLAUDE_PROFILE = make_claude_profile()

AUTH_FAILURE_MODAL_PANE = (
    "Please run /login · API Error: 401 Invalid authentication credentials\n"
)


def _record_terminations(monkeypatch, terminated_process_ids):
    def terminate_and_record(root_process_id: int) -> None:
        terminated_process_ids.append(root_process_id)
        session_watchdog.os.kill(root_process_id, 9)

    monkeypatch.setattr(
        session_watchdog, "terminate_process_tree", terminate_and_record
    )


def test_watchdog_terminates_session_when_pane_is_frozen_and_not_idle(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog,
        "capture_pane_content",
        lambda _tmux_target: AUTH_FAILURE_MODAL_PANE,
    )
    terminated_process_ids: list[int] = []
    _record_terminations(monkeypatch, terminated_process_ids)

    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 30",
            None,
            "clawde:golden",
            CLAUDE_PROFILE,
        )
    )
    assert was_stuck_kill is True
    assert len(terminated_process_ids) == 1


def test_watchdog_terminates_when_heartbeat_driver_gives_up_on_repl(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog, "capture_pane_content", lambda _tmux_target: None
    )
    terminated_process_ids: list[int] = []
    _record_terminations(monkeypatch, terminated_process_ids)

    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 30",
            ["bash", "-c", "exit 1"],
            "clawde:steward",
            CLAUDE_PROFILE,
        )
    )
    assert was_stuck_kill is True, (
        "when the heartbeat driver exits because it never found a live REPL, the "
        "session is wedged at a pre-prompt modal (e.g. the resume-confirmation "
        "dialog) and the watchdog must terminate it to force a fresh restart"
    )
    assert len(terminated_process_ids) == 1


def test_session_argv_is_exposed_verbatim_to_launch_command(tmp_path):
    captured_argv = tmp_path / "argv.txt"
    session_watchdog.run_launch_command_once(
        f'printf "%s" "$CLAWDE_SESSION_ARGV" > "{captured_argv}"',
        None,
        None,
        CLAUDE_PROFILE,
        session_argv="--resume pinned-session-id",
    )
    assert captured_argv.read_text() == "--resume pinned-session-id"


def test_default_launch_leaves_session_argv_empty(tmp_path):
    captured_argv = tmp_path / "argv.txt"
    session_watchdog.run_launch_command_once(
        f'printf "%s" "$CLAWDE_SESSION_ARGV" > "{captured_argv}"',
        None,
        None,
        CLAUDE_PROFILE,
    )
    assert captured_argv.read_text() == ""


def test_agent_name_is_exported_as_the_autonomous_agent_marker(tmp_path):
    captured_name = tmp_path / "name.txt"
    session_watchdog.run_launch_command_once(
        f'printf "%s" "$CLAWDE_AGENT_NAME" > "{captured_name}"',
        None,
        None,
        CLAUDE_PROFILE,
        agent_name="steward",
    )
    assert captured_name.read_text() == "steward", (
        "a codex agent's fresh launch has an empty session argv, so the agent name "
        "is the only always-set marker downstream tooling can key off to tell an "
        "autonomous agent session from an interactive one"
    )


def test_register_child_pid_callback_receives_live_then_none(tmp_path):
    observed_process_ids = []
    session_watchdog.run_launch_command_once(
        "true",
        None,
        None,
        CLAUDE_PROFILE,
        register_child_pid=observed_process_ids.append,
    )
    assert len(observed_process_ids) == 2
    assert isinstance(observed_process_ids[0], int)
    assert observed_process_ids[1] is None
