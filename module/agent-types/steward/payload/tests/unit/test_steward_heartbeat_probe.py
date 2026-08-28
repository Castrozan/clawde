import io
import json
from contextlib import redirect_stdout

from steward_test_helpers import steward_heartbeat_probe


def diverged_status(**overrides) -> dict:
    status = {
        "verdict": "needs_sync",
        "head": "ba1418b8",
        "upstream": "0203c361",
        "behind": 1,
        "ahead": 1,
        "dirty": True,
        "inbox_unread": [],
        "continuous_integration": {"state": "passing", "url": "first"},
        "attention_required": True,
    }
    status.update(overrides)
    return status


def run_probe_capturing_output(monkeypatch, status) -> str:
    monkeypatch.setattr(
        steward_heartbeat_probe, "collect_steward_status", lambda: status
    )
    captured = io.StringIO()
    with redirect_stdout(captured):
        steward_heartbeat_probe.main()
    return captured.getvalue()


def test_clean_status_emits_no_fingerprint(monkeypatch):
    output = run_probe_capturing_output(
        monkeypatch, {"verdict": "clean", "attention_required": False}
    )
    assert output.strip() == ""


def test_attention_status_emits_fingerprint(monkeypatch):
    output = run_probe_capturing_output(monkeypatch, diverged_status())
    assert output.strip() != ""


def test_fingerprint_tracks_decision_fields_not_volatile_detail():
    base = steward_heartbeat_probe.decision_fingerprint(diverged_status())
    same_state_new_url = steward_heartbeat_probe.decision_fingerprint(
        diverged_status(continuous_integration={"state": "passing", "url": "second"})
    )
    assert base == same_state_new_url


def test_fingerprint_changes_when_continuous_integration_starts_failing():
    passing = steward_heartbeat_probe.decision_fingerprint(diverged_status())
    failing = steward_heartbeat_probe.decision_fingerprint(
        diverged_status(continuous_integration={"state": "failing", "url": "x"})
    )
    assert passing != failing


def test_a_run_moving_through_its_pending_states_raises_no_edge():
    unfinished = [
        steward_heartbeat_probe.decision_fingerprint(
            diverged_status(continuous_integration={"state": state, "url": "x"})
        )
        for state in ("none", "pending", "passing")
    ]
    assert len(set(unfinished)) == 1


def test_a_peer_moving_the_shared_checkout_raises_no_edge():
    before = steward_heartbeat_probe.decision_fingerprint(diverged_status())
    after = steward_heartbeat_probe.decision_fingerprint(
        diverged_status(head="cafef00d", upstream="cafef00d", dirty=False)
    )
    assert before == after


def test_fingerprint_changes_when_the_checkout_falls_behind():
    before = steward_heartbeat_probe.decision_fingerprint(diverged_status(behind=1))
    after = steward_heartbeat_probe.decision_fingerprint(diverged_status(behind=2))
    assert before != after


def test_fingerprint_changes_when_the_inbox_receives_a_message():
    empty = steward_heartbeat_probe.decision_fingerprint(diverged_status())
    delivered = steward_heartbeat_probe.decision_fingerprint(
        diverged_status(inbox_unread=["1787959285-from-rin.json"])
    )
    assert empty != delivered


def test_fingerprint_is_stable_json(monkeypatch):
    fingerprint = steward_heartbeat_probe.decision_fingerprint(diverged_status())
    assert json.loads(fingerprint)["continuous_integration_failing"] is False
