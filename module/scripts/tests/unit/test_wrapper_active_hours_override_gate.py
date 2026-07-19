import importlib.util
import json
import pathlib
import sys

import pytest

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)
sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))


def _load_wrapper_module():
    module_spec = importlib.util.spec_from_file_location(
        "wrapper", AGENT_WRAPPER_DIRECTORY / "wrapper.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


wrapper = _load_wrapper_module()
agent_launch_iterations = sys.modules["agent_launch_iterations"]


class _StopSupervising(Exception):
    pass


def _write_launch_config_with_active_hours(config_path, active_hours_start):
    config_path.write_text(
        json.dumps(
            {
                "launch_command": "claude",
                "heartbeat_driver_argv": None,
                "active_hours_start": active_hours_start,
                "active_hours_end": 20,
                "daily_session_rotation": False,
                "tmux_session": None,
            }
        )
    )


def _write_override(override_file, active_until_iso):
    override_file.parent.mkdir(parents=True, exist_ok=True)
    override_file.write_text(json.dumps({"active_until": active_until_iso}))


def _build_runtime_layout(tmp_path, active_hours_start, override_active_until_iso):
    config_file = tmp_path / "launch-config" / "steward.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    _write_launch_config_with_active_hours(config_file, active_hours_start)
    override_file = tmp_path / "active-hours-override" / "steward.json"
    if override_active_until_iso is not None:
        _write_override(override_file, override_active_until_iso)
    return config_file, override_file


def _stop_on_run(monkeypatch):
    def fake_run_launch_command_once(*_args, **_kwargs):
        raise _StopSupervising()

    monkeypatch.setattr(
        agent_launch_iterations,
        "run_launch_command_once",
        fake_run_launch_command_once,
    )
    monkeypatch.setattr(wrapper.time, "sleep", lambda seconds: None)


def test_supervise_runs_outside_hours_when_override_unexpired(monkeypatch, tmp_path):
    config_file, override_file = _build_runtime_layout(
        tmp_path, 8, "2999-01-01T00:00:00"
    )
    _stop_on_run(monkeypatch)
    monkeypatch.setattr(
        wrapper,
        "is_within_active_hours",
        lambda start, end, now=None, active_weekdays_only=False: False,
    )

    with pytest.raises(_StopSupervising):
        wrapper.supervise_agent_forever("steward", str(config_file))

    assert override_file.exists()


def test_supervise_sleeps_and_clears_override_when_expired(monkeypatch, tmp_path):
    config_file, override_file = _build_runtime_layout(
        tmp_path, 8, "2000-01-01T00:00:00"
    )

    def fake_sleep(seconds):
        raise _StopSupervising()

    monkeypatch.setattr(
        wrapper,
        "is_within_active_hours",
        lambda start, end, now=None, active_weekdays_only=False: False,
    )
    monkeypatch.setattr(wrapper.time, "sleep", fake_sleep)

    with pytest.raises(_StopSupervising):
        wrapper.supervise_agent_forever("steward", str(config_file))

    assert not override_file.exists()


def test_supervise_clears_lingering_override_within_active_hours(monkeypatch, tmp_path):
    config_file, override_file = _build_runtime_layout(
        tmp_path, 8, "2999-01-01T00:00:00"
    )
    _stop_on_run(monkeypatch)
    monkeypatch.setattr(
        wrapper,
        "is_within_active_hours",
        lambda start, end, now=None, active_weekdays_only=False: True,
    )

    with pytest.raises(_StopSupervising):
        wrapper.supervise_agent_forever("steward", str(config_file))

    assert not override_file.exists()
