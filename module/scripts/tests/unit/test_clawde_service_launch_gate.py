import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service")
)
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import launch_gate_decision
from clawde_service_test_helpers import load_service_module

service_module = load_service_module()


def _scheduler_with_configuration(monkeypatch, launch_gate_command, interval_seconds):
    monkeypatch.setattr(
        launch_gate_decision,
        "launch_gate_configuration_for_agent",
        lambda agent_name: (launch_gate_command, interval_seconds),
    )
    return launch_gate_decision.LaunchGateScheduler()


def _wait_for_pending_launch(scheduler, agent_name, timeout_seconds=5.0):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if scheduler.launch_is_pending(agent_name):
            return True
        time.sleep(0.02)
    return False


def test_a_warm_agent_never_reports_a_pending_launch(monkeypatch):
    scheduler = _scheduler_with_configuration(monkeypatch, None, None)

    assert scheduler.launch_is_pending("jenny") is False


def test_a_firing_gate_becomes_a_pending_launch(monkeypatch):
    scheduler = _scheduler_with_configuration(monkeypatch, "exit 0", 900)

    assert _wait_for_pending_launch(scheduler, "steward") is True


def test_a_silent_gate_never_becomes_a_pending_launch(monkeypatch):
    scheduler = _scheduler_with_configuration(monkeypatch, "exit 1", 900)

    assert _wait_for_pending_launch(scheduler, "steward", timeout_seconds=1.0) is False


def test_the_probe_is_throttled_to_the_configured_interval(monkeypatch):
    scheduler = _scheduler_with_configuration(monkeypatch, "gate", 900)
    probe_invocations = []
    monkeypatch.setattr(
        launch_gate_decision,
        "run_launch_gate_probe",
        lambda command: probe_invocations.append(command) or False,
    )

    for _poll in range(5):
        scheduler.launch_is_pending("steward")
        time.sleep(0.05)

    assert len(probe_invocations) == 1


def test_consuming_a_pending_launch_clears_it(monkeypatch):
    scheduler = _scheduler_with_configuration(monkeypatch, "exit 0", 900)
    assert _wait_for_pending_launch(scheduler, "steward") is True

    scheduler.consume_pending_launch("steward")

    assert scheduler.launch_is_pending("steward") is False


def test_a_gate_without_a_command_fires_every_interval(monkeypatch):
    scheduler = _scheduler_with_configuration(monkeypatch, None, 900)

    assert scheduler.launch_is_pending("steward") is True


def test_a_probe_that_times_out_does_not_fire_the_gate(monkeypatch):
    monkeypatch.setattr(launch_gate_decision, "LAUNCH_GATE_PROBE_TIMEOUT_SECONDS", 0.05)

    assert launch_gate_decision.run_launch_gate_probe("sleep 30") is False


def _triggered_session_specification():
    return {
        "name": "clawde",
        "agents": [{"name": "steward", "wrapper_command": "wrap steward"}],
    }


def _patch_service_for_triggered_steward(monkeypatch, agent_names_with_live_wrapper):
    monkeypatch.setattr(
        service_module.active_hours_decision,
        "agent_should_run_now",
        lambda agent_name, now=None: True,
    )
    monkeypatch.setattr(
        service_module.launch_gate_decision,
        "agent_launches_on_trigger",
        lambda agent_name: True,
    )
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_live_wrapper",
        lambda session_name: set(agent_names_with_live_wrapper),
    )
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_running_wrapper_after_reconcile",
        lambda session_name, should_run: set(agent_names_with_live_wrapper)
        & should_run,
    )


class _RecordingBackend:
    def __init__(self):
        self.ensured_windows = []
        self.removed_windows = []

    def ensure_host_ready(self, session_name):
        return False

    def ensure_agent_window(self, session_name, agent_name, wrapper_command):
        self.ensured_windows.append(agent_name)
        return False

    def remove_agent_window(self, session_name, agent_name):
        self.removed_windows.append(agent_name)

    def remove_bootstrap_scaffolding(self, session_name):
        pass


class _PendingScheduler:
    def __init__(self, pending):
        self.pending = pending
        self.consumed = []

    def launch_is_pending(self, agent_name):
        return self.pending

    def consume_pending_launch(self, agent_name):
        self.consumed.append(agent_name)


def test_a_dormant_triggered_agent_holds_no_window(monkeypatch):
    _patch_service_for_triggered_steward(monkeypatch, set())
    backend = _RecordingBackend()

    service_module.ensure_agent_windows_for_session(
        backend, _triggered_session_specification(), _PendingScheduler(False)
    )

    assert backend.ensured_windows == []
    assert backend.removed_windows == ["steward"]


def test_a_pending_launch_spawns_the_window(monkeypatch):
    _patch_service_for_triggered_steward(monkeypatch, set())
    backend = _RecordingBackend()

    service_module.ensure_agent_windows_for_session(
        backend, _triggered_session_specification(), _PendingScheduler(True)
    )

    assert backend.ensured_windows == ["steward"]
    assert backend.removed_windows == []


def test_an_in_flight_cycle_is_kept_and_consumes_its_pending_launch(monkeypatch):
    _patch_service_for_triggered_steward(monkeypatch, {"steward"})
    backend = _RecordingBackend()
    scheduler = _PendingScheduler(False)

    service_module.ensure_agent_windows_for_session(
        backend, _triggered_session_specification(), scheduler
    )

    assert backend.removed_windows == []
    assert scheduler.consumed == ["steward"]
