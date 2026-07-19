import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from clawde_service_test_helpers import (
    load_service_module,
    make_tmux_supervisor_backend,
    recording_fake_tmux,
)

service_module = load_service_module()


class RecordingBackend:
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


def _session_specification(agent_names):
    return {
        "name": "clawde",
        "agents": [
            {"name": agent_name, "wrapper_command": f"wrap {agent_name}"}
            for agent_name in agent_names
        ],
    }


def _patch_should_run(monkeypatch, agent_names_that_should_run):
    monkeypatch.setattr(
        service_module.active_hours_decision,
        "agent_should_run_now",
        lambda agent_name, now=None: agent_name in agent_names_that_should_run,
    )


def _patch_reconcile(monkeypatch, agent_names_with_running_wrapper, recorded_sets):
    def fake_reconcile(session_name, agent_names_that_should_be_running):
        recorded_sets.append(set(agent_names_that_should_be_running))
        return set(agent_names_with_running_wrapper) & set(
            agent_names_that_should_be_running
        )

    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_running_wrapper_after_reconcile",
        fake_reconcile,
    )


def test_off_hours_agent_window_is_removed_and_not_spawned(monkeypatch):
    _patch_should_run(monkeypatch, {"steward"})
    _patch_reconcile(
        monkeypatch, agent_names_with_running_wrapper=set(), recorded_sets=[]
    )
    backend = RecordingBackend()

    service_module.ensure_agent_windows_for_session(
        backend, _session_specification(["steward", "betha-pm"])
    )

    assert backend.removed_windows == ["betha-pm"]
    assert backend.ensured_windows == ["steward"]


def test_reconcile_is_scoped_to_agents_that_should_be_running(monkeypatch):
    _patch_should_run(monkeypatch, {"steward"})
    recorded_sets = []
    _patch_reconcile(
        monkeypatch,
        agent_names_with_running_wrapper={"steward", "betha-pm"},
        recorded_sets=recorded_sets,
    )
    backend = RecordingBackend()

    service_module.ensure_agent_windows_for_session(
        backend, _session_specification(["steward", "betha-pm"])
    )

    assert recorded_sets == [{"steward"}]
    assert backend.removed_windows == ["betha-pm"]


def test_active_agent_with_running_wrapper_is_not_respawned(monkeypatch):
    _patch_should_run(monkeypatch, {"steward", "betha-pm"})
    _patch_reconcile(
        monkeypatch,
        agent_names_with_running_wrapper={"steward", "betha-pm"},
        recorded_sets=[],
    )
    backend = RecordingBackend()

    service_module.ensure_agent_windows_for_session(
        backend, _session_specification(["steward", "betha-pm"])
    )

    assert backend.ensured_windows == []
    assert backend.removed_windows == []


def test_active_agent_without_a_wrapper_is_spawned(monkeypatch):
    _patch_should_run(monkeypatch, {"steward"})
    _patch_reconcile(
        monkeypatch, agent_names_with_running_wrapper=set(), recorded_sets=[]
    )
    backend = RecordingBackend()

    service_module.ensure_agent_windows_for_session(
        backend, _session_specification(["steward"])
    )

    assert backend.ensured_windows == ["steward"]


def test_tmux_remove_agent_window_kills_the_named_window():
    fake_run_tmux_command, issued_commands = recording_fake_tmux(set(), {})
    backend = make_tmux_supervisor_backend(fake_run_tmux_command)

    backend.remove_agent_window("clawde", "betha-pm")

    assert ("kill-window", "-t", "clawde:betha-pm") in issued_commands
