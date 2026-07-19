import pathlib
import sys
import types

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import agent_launch_iterations


def _fake_launch_session():
    return types.SimpleNamespace(
        resume_flag="--resume abc",
        resume_previous_session=True,
        rotating_session=False,
        session_record_file_path="/tmp/steward-session.json",
    )


def _patch_common(monkeypatch, resume_session_missing=False):
    monkeypatch.setattr(
        agent_launch_iterations,
        "decide_and_persist_launch_session",
        lambda *args, **kwargs: _fake_launch_session(),
    )
    launches = []
    monkeypatch.setattr(
        agent_launch_iterations,
        "run_launch_command_to_completion",
        lambda launch_command, *args, **kwargs: launches.append(launch_command)
        or (1.0, False, resume_session_missing),
    )
    slept = []
    monkeypatch.setattr(
        agent_launch_iterations.time, "sleep", lambda seconds: slept.append(seconds)
    )
    return launches, slept


def test_triggered_iteration_launches_once_when_the_gate_fires(monkeypatch):
    launches, slept = _patch_common(monkeypatch)
    monkeypatch.setattr(agent_launch_iterations, "launch_gate_fires", lambda _cmd: True)

    agent_launch_iterations.run_triggered_launch_iteration(
        "steward", "claude --print x", None, "/root", False, "probe", 900
    )

    assert launches == ["claude --print x"]
    assert slept == [900]


def test_triggered_iteration_skips_the_launch_when_the_gate_does_not_fire(monkeypatch):
    launches, slept = _patch_common(monkeypatch)
    monkeypatch.setattr(
        agent_launch_iterations, "launch_gate_fires", lambda _cmd: False
    )

    agent_launch_iterations.run_triggered_launch_iteration(
        "steward", "claude --print x", None, "/root", False, "probe", 900
    )

    assert launches == []
    assert slept == [900]


def test_triggered_iteration_drops_a_missing_resume_session(monkeypatch):
    _launches, _slept = _patch_common(monkeypatch, resume_session_missing=True)
    monkeypatch.setattr(agent_launch_iterations, "launch_gate_fires", lambda _cmd: True)
    cleared_records = []
    monkeypatch.setattr(
        agent_launch_iterations,
        "clear_persisted_session_record",
        lambda record_path: cleared_records.append(record_path),
    )

    agent_launch_iterations.run_triggered_launch_iteration(
        "steward", "claude --print x", None, "/root", False, "probe", 900
    )

    assert cleared_records == ["/tmp/steward-session.json"]
