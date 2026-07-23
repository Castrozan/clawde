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
        session_identifier="abc",
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


def test_triggered_iteration_launches_once_and_never_sleeps(monkeypatch):
    launches, slept = _patch_common(monkeypatch)

    agent_launch_iterations.run_triggered_launch_iteration(
        "steward", "claude --print x", None, "/root", False
    )

    assert launches == ["claude --print x"]
    assert slept == []


def test_triggered_iteration_drops_only_the_missing_resume_session(monkeypatch):
    _launches, _slept = _patch_common(monkeypatch, resume_session_missing=True)
    forgotten = []
    monkeypatch.setattr(
        agent_launch_iterations,
        "forget_session_identifier_from_record",
        lambda record_path, session_identifier: forgotten.append(
            (record_path, session_identifier)
        ),
    )

    agent_launch_iterations.run_triggered_launch_iteration(
        "steward", "claude --print x", None, "/root", False
    )

    assert forgotten == [("/tmp/steward-session.json", "abc")]
