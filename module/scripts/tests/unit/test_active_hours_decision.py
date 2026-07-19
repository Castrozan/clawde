import datetime
import json
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import active_hours_decision


def _write_launch_config(home_directory, agent_name, launch_config):
    launch_config_directory = home_directory / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    (launch_config_directory / f"{agent_name}.json").write_text(
        json.dumps(launch_config)
    )


def _write_override(home_directory, agent_name, active_until):
    override_directory = home_directory / "clawde" / "active-hours-override"
    override_directory.mkdir(parents=True, exist_ok=True)
    (override_directory / f"{agent_name}.json").write_text(
        json.dumps({"active_until": active_until.isoformat()})
    )


def test_agent_within_active_hours_on_a_weekday_should_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path, "betha-pm", {"active_hours_start": 8, "active_hours_end": 20}
    )
    monday_noon = datetime.datetime(2026, 7, 20, 12, 0, 0)
    assert active_hours_decision.agent_should_run_now("betha-pm", now=monday_noon)


def test_agent_outside_active_hours_should_not_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path, "betha-pm", {"active_hours_start": 8, "active_hours_end": 20}
    )
    monday_night = datetime.datetime(2026, 7, 20, 23, 0, 0)
    assert not active_hours_decision.agent_should_run_now("betha-pm", now=monday_night)


def test_weekday_only_agent_should_not_run_on_the_weekend(tmp_path, monkeypatch):
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
    sunday_noon = datetime.datetime(2026, 7, 19, 12, 0, 0)
    assert not active_hours_decision.agent_should_run_now("betha-pm", now=sunday_noon)


def test_active_hours_override_forces_an_off_hours_agent_to_run(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(
        tmp_path, "betha-pm", {"active_hours_start": 8, "active_hours_end": 20}
    )
    monday_night = datetime.datetime(2026, 7, 20, 23, 0, 0)
    _write_override(tmp_path, "betha-pm", monday_night + datetime.timedelta(hours=2))
    assert active_hours_decision.agent_should_run_now("betha-pm", now=monday_night)


def test_agent_without_active_hours_gate_always_runs(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(tmp_path, "steward", {"active_hours_start": None})
    weekend_night = datetime.datetime(2026, 7, 19, 3, 0, 0)
    assert active_hours_decision.agent_should_run_now("steward", now=weekend_night)


def test_missing_launch_config_fails_open_to_running(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monday_night = datetime.datetime(2026, 7, 20, 23, 0, 0)
    assert active_hours_decision.agent_should_run_now(
        "never-deployed", now=monday_night
    )
