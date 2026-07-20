import datetime
import json
import pathlib
import sys

import pytest

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import on_demand_control
import on_demand_lease

AGENT_NAME = "on-demand-agent"
STARTED_AT = datetime.datetime(2026, 7, 20, 10, 0, 0)


def deploy_agent(home_directory, launch_config):
    launch_config_directory = home_directory / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    (launch_config_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(launch_config)
    )


def lease_file_path(home_directory):
    return on_demand_lease.lease_file_path_for_agent(
        str(home_directory / "clawde"), AGENT_NAME
    )


def test_starting_an_on_demand_agent_writes_its_lease(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True, "idle_timeout_minutes": 45})

    on_demand_control.start_agent_on_demand(AGENT_NAME, STARTED_AT)

    assert (
        on_demand_lease.read_lease_started_at(lease_file_path(tmp_path)) == STARTED_AT
    )
    assert "45 minutes" in capsys.readouterr().out


def test_starting_reports_a_fresh_session_when_no_conversation_exists(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True, "workspace_directory": "/repo/project"})

    on_demand_control.start_agent_on_demand(AGENT_NAME, STARTED_AT)

    assert "starting a fresh session" in capsys.readouterr().out


def test_starting_reports_the_resumed_session_when_its_conversation_exists(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HOME", str(tmp_path))
    workspace_directory = "/repo/project"
    deploy_agent(
        tmp_path, {"on_demand": True, "workspace_directory": workspace_directory}
    )
    session_directory = tmp_path / "clawde" / "session-ids"
    session_directory.mkdir(parents=True)
    (session_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(
            {"session_identifier": "session-one", "started_on_date": "2026-07-19"}
        )
    )
    project_directory = (
        tmp_path / ".claude" / "projects" / workspace_directory.replace("/", "-")
    )
    project_directory.mkdir(parents=True)
    (project_directory / "session-one.jsonl").write_text("{}\n")

    on_demand_control.start_agent_on_demand(AGENT_NAME, STARTED_AT)

    assert "resuming session session-one" in capsys.readouterr().out


def test_starting_a_supervised_agent_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": False})

    with pytest.raises(SystemExit):
        on_demand_control.start_agent_on_demand(AGENT_NAME, STARTED_AT)


def test_stopping_an_on_demand_agent_clears_its_lease(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True})
    on_demand_control.start_agent_on_demand(AGENT_NAME, STARTED_AT)
    capsys.readouterr()

    on_demand_control.stop_agent_on_demand(AGENT_NAME)

    assert on_demand_lease.read_lease_started_at(lease_file_path(tmp_path)) is None
    assert "Stopped" in capsys.readouterr().out


def test_stopping_an_already_stopped_agent_says_so(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True})

    on_demand_control.stop_agent_on_demand(AGENT_NAME)

    assert "already stopped" in capsys.readouterr().out


def test_stopping_a_supervised_agent_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": False})

    with pytest.raises(SystemExit):
        on_demand_control.stop_agent_on_demand(AGENT_NAME)
