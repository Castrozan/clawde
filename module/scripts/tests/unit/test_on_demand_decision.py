import datetime
import json
import os
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import on_demand_decision
import on_demand_lease

AGENT_NAME = "on-demand-agent"


def deploy_agent(home_directory, launch_config, session_identifier=None):
    launch_config_directory = home_directory / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    (launch_config_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(launch_config)
    )
    if session_identifier is None:
        return
    session_directory = home_directory / "clawde" / "session-ids"
    session_directory.mkdir(parents=True, exist_ok=True)
    (session_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(
            {"session_identifier": session_identifier, "started_on_date": "2026-07-20"}
        )
    )


def write_transcript(home_directory, workspace_directory, session_identifier, mtime):
    project_directory = (
        home_directory
        / ".claude"
        / "projects"
        / (str(workspace_directory).replace("/", "-"))
    )
    project_directory.mkdir(parents=True, exist_ok=True)
    transcript_file = project_directory / f"{session_identifier}.jsonl"
    transcript_file.write_text("{}\n")
    epoch_seconds = mtime.timestamp()
    os.utime(transcript_file, (epoch_seconds, epoch_seconds))


def grant_lease(home_directory, started_at):
    on_demand_lease.write_lease_started_at(
        on_demand_lease.lease_file_path_for_agent(
            str(home_directory / "clawde"), AGENT_NAME
        ),
        started_at,
    )


def test_agent_without_the_flag_does_not_run_on_demand(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": False})

    assert not on_demand_decision.agent_runs_on_demand(AGENT_NAME)


def test_agent_with_an_unreadable_launch_config_does_not_run_on_demand(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    launch_config_directory = tmp_path / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True)
    (launch_config_directory / f"{AGENT_NAME}.json").write_text("not json{{{")

    assert not on_demand_decision.agent_runs_on_demand(AGENT_NAME)


def test_agent_with_the_flag_runs_on_demand(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True})

    assert on_demand_decision.agent_runs_on_demand(AGENT_NAME)


def test_without_a_lease_the_agent_is_not_allowed_to_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True, "idle_timeout_minutes": 30})

    assert not on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 10, 0, 0)
    )


def test_a_fresh_lease_allows_the_agent_to_run_without_any_transcript(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True, "idle_timeout_minutes": 30})
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 10, 1, 0)
    )


def test_a_stale_transcript_does_not_make_a_fresh_lease_immediately_idle(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    workspace_directory = "/repo/project"
    deploy_agent(
        tmp_path,
        {
            "on_demand": True,
            "idle_timeout_minutes": 30,
            "workspace_directory": workspace_directory,
        },
        session_identifier="session-one",
    )
    write_transcript(
        tmp_path,
        workspace_directory,
        "session-one",
        datetime.datetime(2026, 7, 15, 9, 0, 0),
    )
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 10, 1, 0)
    )


def test_conversation_activity_keeps_the_lease_alive_past_the_lease_start(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    workspace_directory = "/repo/project"
    deploy_agent(
        tmp_path,
        {
            "on_demand": True,
            "idle_timeout_minutes": 30,
            "workspace_directory": workspace_directory,
        },
        session_identifier="session-one",
    )
    write_transcript(
        tmp_path,
        workspace_directory,
        "session-one",
        datetime.datetime(2026, 7, 20, 11, 50, 0),
    )
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 12, 0, 0)
    )


def test_an_idle_lease_stops_the_agent_and_is_cleared(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True, "idle_timeout_minutes": 30})
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert not on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 10, 31, 0)
    )
    assert (
        on_demand_lease.read_lease_started_at(
            on_demand_lease.lease_file_path_for_agent(
                str(tmp_path / "clawde"), AGENT_NAME
            )
        )
        is None
    )


def test_a_missing_idle_timeout_falls_back_to_the_default(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, {"on_demand": True})

    _on_demand, idle_timeout_minutes = (
        on_demand_decision.on_demand_configuration_for_agent(AGENT_NAME)
    )

    assert idle_timeout_minutes == on_demand_decision.DEFAULT_IDLE_TIMEOUT_MINUTES
