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


def _write_launch_config(config_path, launch_command, daily_session_rotation=False):
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "launch_command": launch_command,
                "heartbeat_driver_argv": None,
                "active_hours_start": None,
                "active_hours_end": None,
                "daily_session_rotation": daily_session_rotation,
                "tmux_session": None,
            }
        )
    )


def _launch_config_path(tmp_path):
    return tmp_path / "launch-config" / "agent.json"


def _run_supervisor_capturing_resume_flags(monkeypatch, config_file, run_results):
    observed_resume_flags = []

    def fake_run_launch_command_once(
        launch_command, heartbeat_driver_argv, tmux_target, **kwargs
    ):
        index = len(observed_resume_flags)
        observed_resume_flags.append(kwargs.get("resume_flag"))
        if index < len(run_results):
            return run_results[index]
        raise _StopSupervising()

    monkeypatch.setattr(
        agent_launch_iterations,
        "run_launch_command_once",
        fake_run_launch_command_once,
    )
    monkeypatch.setattr(
        wrapper,
        "is_within_active_hours",
        lambda start, end, now=None, active_weekdays_only=False: True,
    )
    monkeypatch.setattr(wrapper.time, "sleep", lambda seconds: None)

    with pytest.raises(_StopSupervising):
        wrapper.supervise_agent_forever("steward", str(config_file))
    return observed_resume_flags


def test_load_agent_launch_config_reads_json(tmp_path):
    config_file = _launch_config_path(tmp_path)
    _write_launch_config(config_file, "claude --name steward")
    assert (
        wrapper.load_agent_launch_config(str(config_file))["launch_command"]
        == "claude --name steward"
    )


def test_supervise_rereads_config_on_each_restart(monkeypatch, tmp_path):
    config_file = _launch_config_path(tmp_path)
    _write_launch_config(config_file, "first")
    launch_commands_run = []

    def fake_run_launch_command_once(
        launch_command, heartbeat_driver_argv, tmux_target, **_kwargs
    ):
        launch_commands_run.append(launch_command)
        if len(launch_commands_run) == 1:
            _write_launch_config(config_file, "second")
            return (0.0, False, False)
        raise _StopSupervising()

    monkeypatch.setattr(
        agent_launch_iterations,
        "run_launch_command_once",
        fake_run_launch_command_once,
    )
    monkeypatch.setattr(
        wrapper,
        "is_within_active_hours",
        lambda start, end, now=None, active_weekdays_only=False: True,
    )
    monkeypatch.setattr(wrapper.time, "sleep", lambda seconds: None)

    with pytest.raises(_StopSupervising):
        wrapper.supervise_agent_forever("steward", str(config_file))

    assert launch_commands_run == ["first", "second"]


def test_supervise_resumes_the_pinned_session_on_the_next_restart(
    monkeypatch, tmp_path
):
    config_file = _launch_config_path(tmp_path)
    _write_launch_config(config_file, "claude")
    observed = _run_supervisor_capturing_resume_flags(
        monkeypatch, config_file, [(0.0, False, False)]
    )

    fresh_launch_flag, restart_resume_flag = observed
    assert fresh_launch_flag.startswith("--session-id ")
    pinned_session_id = fresh_launch_flag.removeprefix("--session-id ")
    assert restart_resume_flag == f"--resume {pinned_session_id}", (
        "when the agent process dies and the supervisor relaunches it, the wrapper "
        "must resume the exact session id the previous launch pinned to disk"
    )


def test_supervise_drops_a_dead_session_and_relaunches_fresh(monkeypatch, tmp_path):
    config_file = _launch_config_path(tmp_path)
    _write_launch_config(config_file, "claude")
    observed = _run_supervisor_capturing_resume_flags(
        monkeypatch, config_file, [(0.0, False, False), (0.0, False, True)]
    )

    fresh_launch_flag, resume_flag, relaunch_flag = observed
    pinned_session_id = fresh_launch_flag.removeprefix("--session-id ")
    assert resume_flag == f"--resume {pinned_session_id}"
    assert relaunch_flag.startswith("--session-id "), (
        "after a resume reports the session no longer exists, the wrapper must drop "
        "the stale id and pin a brand-new session instead of resuming it forever"
    )
    assert relaunch_flag.removeprefix("--session-id ") != pinned_session_id


def test_supervise_retries_when_config_unreadable(monkeypatch, tmp_path):
    recorded_sleeps = []

    def fake_sleep(seconds):
        recorded_sleeps.append(seconds)
        raise _StopSupervising()

    monkeypatch.setattr(wrapper.time, "sleep", fake_sleep)

    with pytest.raises(_StopSupervising):
        wrapper.supervise_agent_forever("steward", str(tmp_path / "missing.json"))

    assert recorded_sleeps
