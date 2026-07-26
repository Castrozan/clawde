import datetime
import json
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import agent_expected_running

SUNDAY_NOON = datetime.datetime(2026, 7, 26, 12, 0, 0)
MONDAY_NOON = datetime.datetime(2026, 7, 20, 12, 0, 0)
MONDAY_NIGHT = datetime.datetime(2026, 7, 20, 23, 0, 0)


def _write_launch_config(home_directory, agent_name, launch_config):
    launch_config_directory = home_directory / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    (launch_config_directory / f"{agent_name}.json").write_text(
        json.dumps(launch_config)
    )


def _write_lease(home_directory, agent_name, started_at):
    lease_directory = home_directory / "clawde" / "on-demand"
    lease_directory.mkdir(parents=True, exist_ok=True)
    (lease_directory / f"{agent_name}.json").write_text(
        json.dumps({"started_at": started_at.isoformat()})
    )


def _lease_file(home_directory, agent_name):
    return home_directory / "clawde" / "on-demand" / f"{agent_name}.json"


def test_weekday_only_agent_is_dormant_on_the_weekend(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path,
        "betha-pm",
        {
            "active_hours_start": 8,
            "active_hours_end": 20,
            "active_weekdays_only": True,
        },
    )
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=SUNDAY_NOON)
        == agent_expected_running.WEEKEND_DORMANCY_REASON
    )


def test_agent_outside_its_hour_window_reports_that_window(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path, "betha-pm", {"active_hours_start": 8, "active_hours_end": 20}
    )
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NIGHT)
        == "outside active hours 8-20"
    )


def test_on_demand_agent_without_a_lease_is_dormant_inside_active_hours(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path,
        "betha-pm",
        {"active_hours_start": 8, "active_hours_end": 20, "on_demand": True},
    )
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NOON)
        == agent_expected_running.ON_DEMAND_NOT_STARTED_REASON
    )


def test_on_demand_agent_with_a_live_lease_is_expected_to_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path,
        "betha-pm",
        {
            "active_hours_start": 8,
            "active_hours_end": 20,
            "on_demand": True,
            "idle_timeout_minutes": 30,
        },
    )
    _write_lease(tmp_path, "betha-pm", MONDAY_NOON - datetime.timedelta(minutes=5))
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NOON)
        is None
    )


def test_on_demand_agent_with_an_idle_lease_is_dormant(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path,
        "betha-pm",
        {
            "active_hours_start": 8,
            "active_hours_end": 20,
            "on_demand": True,
            "idle_timeout_minutes": 30,
        },
    )
    _write_lease(tmp_path, "betha-pm", MONDAY_NOON - datetime.timedelta(hours=4))
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NOON)
        == agent_expected_running.ON_DEMAND_NOT_STARTED_REASON
    )


def test_reading_dormancy_never_clears_an_idle_lease(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path,
        "betha-pm",
        {
            "active_hours_start": 8,
            "active_hours_end": 20,
            "on_demand": True,
            "idle_timeout_minutes": 30,
        },
    )
    _write_lease(tmp_path, "betha-pm", MONDAY_NOON - datetime.timedelta(hours=4))
    agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NOON)
    assert _lease_file(tmp_path, "betha-pm").exists()


def test_always_on_agent_inside_its_window_is_expected_to_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(tmp_path, "steward", {"active_hours_start": None})
    assert (
        agent_expected_running.dormancy_reason_for_agent("steward", now=SUNDAY_NOON)
        is None
    )


def test_weekday_only_agent_inside_its_window_is_expected_to_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path,
        "betha-pm",
        {
            "active_hours_start": 8,
            "active_hours_end": 20,
            "active_weekdays_only": True,
        },
    )
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NOON)
        is None
    )


def test_missing_launch_config_is_expected_to_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert (
        agent_expected_running.dormancy_reason_for_agent(
            "never-deployed", now=MONDAY_NIGHT
        )
        is None
    )


def test_active_hours_override_makes_an_off_hours_agent_expected_to_run(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path, "betha-pm", {"active_hours_start": 8, "active_hours_end": 20}
    )
    override_directory = tmp_path / "clawde" / "active-hours-override"
    override_directory.mkdir(parents=True, exist_ok=True)
    (override_directory / "betha-pm.json").write_text(
        json.dumps(
            {"active_until": (MONDAY_NIGHT + datetime.timedelta(hours=2)).isoformat()}
        )
    )
    assert (
        agent_expected_running.dormancy_reason_for_agent("betha-pm", now=MONDAY_NIGHT)
        is None
    )
