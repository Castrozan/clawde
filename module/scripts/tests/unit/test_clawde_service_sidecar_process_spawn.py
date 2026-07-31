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

import sidecar_process_reconcile
from clawde_service_test_helpers import load_service_module
from sidecar_process_test_support import (
    AGENT_NAME,
    SIDECAR_NAME,
    make_sidecar_specification,
    make_session_specification,
    record_process_lookups,
)

service_module = load_service_module()


def test_sidecar_output_lands_in_its_log_file(tmp_path):
    log_file = tmp_path / "sidecar-logs" / f"{SIDECAR_NAME}.log"

    sidecar_process_reconcile.spawn_sidecar_process(
        make_sidecar_specification(tmp_path, command="echo bridged-agent-is-up")
    )

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if log_file.exists() and "bridged-agent-is-up" in log_file.read_text():
            return
        time.sleep(0.05)
    raise AssertionError(f"sidecar output never reached {log_file}")


def test_spawning_a_sidecar_returns_before_the_sidecar_exits(tmp_path):
    started_at = time.monotonic()

    sidecar_process_reconcile.spawn_sidecar_process(
        make_sidecar_specification(tmp_path, command="sleep 30")
    )

    assert time.monotonic() - started_at < 5


class RecordingSupervisorBackend:
    def __init__(self):
        self.created_window_names = []

    def ensure_host_ready(self, _session_name):
        return False

    def ensure_agent_window(self, _session_name, agent_name, _wrapper_command):
        self.created_window_names.append(agent_name)
        return False

    def remove_agent_window(self, _session_name, _agent_name):
        return None

    def remove_bootstrap_scaffolding(self, _session_name):
        return None


class NeverPendingLaunchGateScheduler:
    def launch_is_pending(self, _agent_name):
        return False

    def consume_pending_launch(self, _agent_name):
        return None


def stub_every_run_decision_to_running(monkeypatch):
    monkeypatch.setattr(
        service_module.active_hours_decision,
        "agent_should_run_now",
        lambda _agent_name: True,
    )
    monkeypatch.setattr(
        service_module.on_demand_decision,
        "agent_runs_on_demand",
        lambda _agent_name: False,
    )
    monkeypatch.setattr(
        service_module.launch_gate_decision,
        "agent_launches_on_trigger",
        lambda _agent_name: False,
    )
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_live_wrapper",
        lambda _session_name: set(),
    )
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_running_wrapper_after_reconcile",
        lambda _session_name, _declared: set(),
    )


def test_a_sidecar_process_never_becomes_a_multiplexer_window(tmp_path, monkeypatch):
    stub_every_run_decision_to_running(monkeypatch)
    record_process_lookups(monkeypatch, [])
    backend = RecordingSupervisorBackend()

    service_module.ensure_agent_windows_for_session(
        backend,
        make_session_specification(tmp_path),
        NeverPendingLaunchGateScheduler(),
    )

    assert backend.created_window_names == [AGENT_NAME]


def test_the_supervisor_reconciles_a_sidecar_on_every_pass(tmp_path, monkeypatch):
    stub_every_run_decision_to_running(monkeypatch)
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])

    service_module.ensure_agent_windows_for_session(
        RecordingSupervisorBackend(),
        make_session_specification(tmp_path),
        NeverPendingLaunchGateScheduler(),
    )

    assert [specification["name"] for specification in spawned_specifications] == [
        SIDECAR_NAME
    ]
