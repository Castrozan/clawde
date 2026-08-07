from agent_wrapper_test_support import IDLE_REPL_PANE, load_agent_wrapper_module
from harness_profile_test_helpers import make_claude_profile

session_watchdog = load_agent_wrapper_module("session_watchdog")

CLAUDE_PROFILE = make_claude_profile()


def run_watchdog_over(monkeypatch, reason_to_replace_session):
    monkeypatch.setattr(session_watchdog, "WATCHDOG_POLL_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(
        session_watchdog, "capture_pane_content", lambda _tmux_target: IDLE_REPL_PANE
    )
    terminated_process_ids: list[int] = []

    def terminate_and_record(root_process_id: int) -> None:
        terminated_process_ids.append(root_process_id)
        session_watchdog.os.kill(root_process_id, 9)

    monkeypatch.setattr(
        session_watchdog, "terminate_process_tree", terminate_and_record
    )
    _runtime_seconds, was_stuck_kill, _resume_session_missing = (
        session_watchdog.run_launch_command_once(
            "sleep 30",
            None,
            "clawde:steward",
            CLAUDE_PROFILE,
            reason_to_replace_session=reason_to_replace_session,
        )
    )
    return terminated_process_ids, was_stuck_kill


def test_the_watchdog_ends_a_session_its_caller_asks_to_replace(monkeypatch):
    terminated_process_ids, was_stuck_kill = run_watchdog_over(
        monkeypatch, lambda: "opencode is refusing work"
    )
    assert len(terminated_process_ids) == 1, (
        "an agent whose harness refuses work sits at a perfectly idle prompt "
        "forever, so nothing else in the watchdog will ever end that session and "
        "the supervisor never gets the chance to move it to another harness"
    )
    assert was_stuck_kill is True


def test_a_session_with_no_replacement_reason_is_left_running(monkeypatch):
    terminated_process_ids, _was_stuck_kill = run_watchdog_over(
        monkeypatch, lambda: None
    )
    assert terminated_process_ids == []


def test_a_caller_that_asks_nothing_leaves_the_session_running(monkeypatch):
    terminated_process_ids, _was_stuck_kill = run_watchdog_over(monkeypatch, None)
    assert terminated_process_ids == []
