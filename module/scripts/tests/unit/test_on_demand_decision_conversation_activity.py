import datetime
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import on_demand_decision
from on_demand_decision_test_support import (
    AGENT_NAME,
    deploy_agent,
    grant_lease,
    write_transcript,
)

WORKSPACE_DIRECTORY = "/repo/project"
ON_DEMAND_LAUNCH_CONFIG = {
    "on_demand": True,
    "idle_timeout_minutes": 30,
    "workspace_directory": WORKSPACE_DIRECTORY,
}


def test_a_stale_transcript_does_not_make_a_fresh_lease_immediately_idle(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, ON_DEMAND_LAUNCH_CONFIG, session_identifier="session-one")
    write_transcript(
        tmp_path,
        WORKSPACE_DIRECTORY,
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
    deploy_agent(tmp_path, ON_DEMAND_LAUNCH_CONFIG, session_identifier="session-one")
    write_transcript(
        tmp_path,
        WORKSPACE_DIRECTORY,
        "session-one",
        datetime.datetime(2026, 7, 20, 11, 50, 0),
    )
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 12, 0, 0)
    )


def test_a_conversation_reopened_under_another_identifier_keeps_the_lease_alive(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(
        tmp_path,
        ON_DEMAND_LAUNCH_CONFIG,
        session_identifier="identifier-the-wrapper-asked-for",
    )
    write_transcript(
        tmp_path,
        WORKSPACE_DIRECTORY,
        "identifier-the-harness-actually-opened",
        datetime.datetime(2026, 7, 20, 11, 50, 0),
    )
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 12, 0, 0)
    ), (
        "a session identifier drifts away from the pinned one whenever the "
        "conversation is cleared, rewound or reopened by the harness, and reading "
        "activity only from the pinned identifier turns that drift into a downscale "
        "of an agent that is in the middle of a conversation"
    )


def test_a_workspace_without_any_transcript_still_goes_idle(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    deploy_agent(tmp_path, ON_DEMAND_LAUNCH_CONFIG, session_identifier="session-one")
    grant_lease(tmp_path, datetime.datetime(2026, 7, 20, 10, 0, 0))

    assert not on_demand_decision.agent_lease_allows_run(
        AGENT_NAME, datetime.datetime(2026, 7, 20, 10, 31, 0)
    )
