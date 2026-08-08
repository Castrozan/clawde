import pytest
from agent_wrapper_test_support import load_agent_wrapper_module

restart_agent = load_agent_wrapper_module("restart_agent")

DEPLOYED_AGENT_NAMES = ["monster", "steward"]
WRAPPER_PROCESS_ID = 231838


@pytest.fixture
def deployed_agents(monkeypatch):
    monkeypatch.setattr(
        restart_agent, "deployed_agent_names", lambda: list(DEPLOYED_AGENT_NAMES)
    )


@pytest.fixture
def terminated_process_ids(monkeypatch):
    recorded_process_ids: list[int] = []
    monkeypatch.setattr(
        restart_agent, "terminate_process_tree", recorded_process_ids.append
    )
    return recorded_process_ids


def set_running_wrapper(monkeypatch, wrapper_process_id_by_agent_name: dict):
    monkeypatch.setattr(
        restart_agent,
        "find_wrapper_process_id_for_agent",
        wrapper_process_id_by_agent_name.get,
    )


def test_restart_terminates_the_whole_wrapper_tree_so_the_harness_dies_with_it(
    deployed_agents, terminated_process_ids, monkeypatch, capsys
):
    set_running_wrapper(monkeypatch, {"monster": WRAPPER_PROCESS_ID})

    restart_agent.restart_agent("monster")

    assert terminated_process_ids == [WRAPPER_PROCESS_ID]
    printed_report = capsys.readouterr().out
    assert "monster" in printed_report
    assert str(WRAPPER_PROCESS_ID) in printed_report


def test_restart_reports_that_the_pinned_session_survives(
    deployed_agents, terminated_process_ids, monkeypatch, capsys
):
    set_running_wrapper(monkeypatch, {"monster": WRAPPER_PROCESS_ID})

    restart_agent.restart_agent("monster")

    assert "resuming its pinned session" in capsys.readouterr().out


def test_an_undeployed_agent_is_refused_before_anything_is_terminated(
    deployed_agents, terminated_process_ids, monkeypatch
):
    set_running_wrapper(monkeypatch, {"monster": WRAPPER_PROCESS_ID})

    with pytest.raises(SystemExit) as refusal:
        restart_agent.restart_agent("frobnicate")

    assert "frobnicate" in str(refusal.value)
    assert "monster, steward" in str(refusal.value)
    assert terminated_process_ids == []


def test_a_deployed_agent_holding_no_wrapper_is_refused_rather_than_reported_restarted(
    deployed_agents, terminated_process_ids, monkeypatch
):
    set_running_wrapper(monkeypatch, {})

    with pytest.raises(SystemExit) as refusal:
        restart_agent.restart_agent("monster")

    assert "holds no wrapper process" in str(refusal.value)
    assert terminated_process_ids == []
