import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import launch_gate


def test_run_launch_command_to_completion_waits_for_a_run_once_command():
    runtime_seconds, exceeded_runtime_cap, resume_session_missing = (
        launch_gate.run_launch_command_to_completion(
            "true",
            tmux_target=None,
            is_resume_launch=False,
        )
    )
    assert exceeded_runtime_cap is False
    assert resume_session_missing is False
    assert runtime_seconds >= 0


def test_run_launch_command_to_completion_terminates_when_it_exceeds_the_cap():
    runtime_seconds, exceeded_runtime_cap, _resume_session_missing = (
        launch_gate.run_launch_command_to_completion(
            "sleep 5",
            tmux_target=None,
            is_resume_launch=False,
            maximum_runtime_seconds=0,
        )
    )
    assert exceeded_runtime_cap is True
    assert runtime_seconds >= 0
