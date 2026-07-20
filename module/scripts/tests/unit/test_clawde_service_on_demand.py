import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service")
)
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import active_hours_decision
import launch_gate_decision
import on_demand_decision
from clawde_service_test_helpers import load_service_module

service_module = load_service_module()

AGENT_NAME = "on-demand-agent"


class NeverPendingLaunchGateScheduler:
    def launch_is_pending(self, _agent_name):
        return False


def configure_agent(monkeypatch, runs_on_demand, lease_allows_run=False):
    monkeypatch.setattr(
        active_hours_decision, "agent_should_run_now", lambda _agent_name: True
    )
    monkeypatch.setattr(
        service_module.active_hours_decision,
        "agent_should_run_now",
        lambda _agent_name: True,
    )
    monkeypatch.setattr(
        service_module.on_demand_decision,
        "agent_runs_on_demand",
        lambda _agent_name: runs_on_demand,
    )
    monkeypatch.setattr(
        service_module.on_demand_decision,
        "agent_lease_allows_run",
        lambda _agent_name: lease_allows_run,
    )
    monkeypatch.setattr(
        service_module.launch_gate_decision,
        "agent_launches_on_trigger",
        lambda _agent_name: False,
    )


def test_an_on_demand_agent_without_a_lease_stays_stopped(monkeypatch):
    configure_agent(monkeypatch, runs_on_demand=True, lease_allows_run=False)

    assert (
        service_module.agent_should_be_running(
            AGENT_NAME, False, NeverPendingLaunchGateScheduler()
        )
        is False
    )


def test_an_on_demand_agent_with_a_live_wrapper_still_stops_once_its_lease_expires(
    monkeypatch,
):
    configure_agent(monkeypatch, runs_on_demand=True, lease_allows_run=False)

    assert (
        service_module.agent_should_be_running(
            AGENT_NAME, True, NeverPendingLaunchGateScheduler()
        )
        is False
    )


def test_an_on_demand_agent_with_a_live_lease_runs(monkeypatch):
    configure_agent(monkeypatch, runs_on_demand=True, lease_allows_run=True)

    assert (
        service_module.agent_should_be_running(
            AGENT_NAME, False, NeverPendingLaunchGateScheduler()
        )
        is True
    )


def test_an_on_demand_agent_outside_active_hours_stays_stopped_despite_its_lease(
    monkeypatch,
):
    configure_agent(monkeypatch, runs_on_demand=True, lease_allows_run=True)
    monkeypatch.setattr(
        service_module.active_hours_decision,
        "agent_should_run_now",
        lambda _agent_name: False,
    )

    assert (
        service_module.agent_should_be_running(
            AGENT_NAME, False, NeverPendingLaunchGateScheduler()
        )
        is False
    )


def test_a_supervised_agent_is_unaffected_by_the_on_demand_gate(monkeypatch):
    configure_agent(monkeypatch, runs_on_demand=False, lease_allows_run=False)

    assert (
        service_module.agent_should_be_running(
            AGENT_NAME, False, NeverPendingLaunchGateScheduler()
        )
        is True
    )


def test_the_on_demand_gate_is_checked_before_the_launch_trigger_gate(monkeypatch):
    configure_agent(monkeypatch, runs_on_demand=True, lease_allows_run=False)
    launch_trigger_was_consulted = []
    monkeypatch.setattr(
        service_module.launch_gate_decision,
        "agent_launches_on_trigger",
        lambda _agent_name: launch_trigger_was_consulted.append(True) or True,
    )

    service_module.agent_should_be_running(
        AGENT_NAME, False, NeverPendingLaunchGateScheduler()
    )

    assert launch_trigger_was_consulted == []


def test_on_demand_decision_and_launch_gate_decision_are_distinct_modules():
    assert on_demand_decision is not launch_gate_decision
