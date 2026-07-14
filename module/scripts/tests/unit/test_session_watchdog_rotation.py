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


def test_watchdog_rotates_long_running_session_at_day_boundary(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog, "capture_pane_content", lambda _tmux_target: IDLE_REPL_PANE
    )
    monkeypatch.setattr(
        session_watchdog,
        "should_rotate_session",
        lambda daily_session_rotation, session_start_date: daily_session_rotation,
    )
    terminated_process_ids: list[int] = []

    def terminate_and_record(root_process_id: int) -> None:
        terminated_process_ids.append(root_process_id)
        session_watchdog.os.kill(root_process_id, session_watchdog.signal.SIGKILL)

    monkeypatch.setattr(
        session_watchdog, "terminate_process_tree", terminate_and_record
    )
    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 30",
            None,
            "clawde:golden",
            daily_session_rotation=True,
        )
    )
    assert was_stuck_kill is False, (
        "a daily rotation is a clean scheduled restart, not a stuck kill, so backoff "
        "must not treat it as a crash"
    )
    assert len(terminated_process_ids) == 1, (
        "a heartbeat-driven agent never exits on its own, so the watchdog must "
        "terminate it once the calendar day rolls over to force the fresh relaunch "
        "that releases accumulated context memory"
    )


def test_watchdog_leaves_session_running_when_rotation_disabled(monkeypatch):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog, "capture_pane_content", lambda _tmux_target: IDLE_REPL_PANE
    )
    monkeypatch.setattr(
        session_watchdog,
        "should_rotate_session",
        lambda daily_session_rotation, session_start_date: daily_session_rotation,
    )
    terminated_process_ids: list[int] = []
    monkeypatch.setattr(
        session_watchdog,
        "terminate_process_tree",
        lambda root_process_id: terminated_process_ids.append(root_process_id),
    )
    session_watchdog.run_launch_command_once(
        "true",
        None,
        "clawde:golden",
        daily_session_rotation=False,
    )
    assert terminated_process_ids == [], (
        "an agent without daily rotation must never be terminated on a day boundary"
    )
