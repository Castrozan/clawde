import importlib.util
import json
import pathlib
import sys

import pytest
from harness_productivity_record import (
    baseline_next_delivery,
    begin_harness_productivity_record,
    harness_productivity_record_path,
)
from harness_profile_test_helpers import (
    CLAUDE_PROFILE_MAPPING,
    CODEX_PROFILE_MAPPING,
)

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)
sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))


class StopSupervising(Exception):
    pass


def load_wrapper_module():
    module_spec = importlib.util.spec_from_file_location(
        "wrapper_failover_test_subject", AGENT_WRAPPER_DIRECTORY / "wrapper.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def write_launch_config(config_file, workspace_directory):
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(
        json.dumps(
            {
                "declared_harness": "claude",
                "harness_fallback_chain": ["codex"],
                "harness_launch_commands": {
                    "claude": "claude",
                    "codex": "codex",
                },
                "harness_runtime_profiles": {
                    "claude": CLAUDE_PROFILE_MAPPING,
                    "codex": CODEX_PROFILE_MAPPING,
                },
                "heartbeat_driver_argv": None,
                "active_hours_start": None,
                "active_hours_end": None,
                "daily_session_rotation": False,
                "tmux_session": None,
                "workspace_directory": str(workspace_directory),
            }
        )
    )


def test_three_crashes_after_delivery_fail_over_to_the_next_harness(
    monkeypatch, tmp_path
):
    wrapper = load_wrapper_module()
    launch_iterations = sys.modules["agent_launch_iterations"]
    config_file = tmp_path / "launch-config" / "steward.json"
    workspace_directory = tmp_path / "workspace"
    write_launch_config(config_file, workspace_directory)
    record_path = harness_productivity_record_path(str(tmp_path), "steward")
    launch_commands_run = []

    def fake_run_launch_command_once(
        launch_command, _heartbeat_driver_argv, _tmux_target, **kwargs
    ):
        launch_commands_run.append(launch_command)
        if launch_command == "codex" or len(launch_commands_run) > 3:
            raise StopSupervising()
        session_identifier = kwargs["session_argv"].split()[-1]
        harness_runtime_profile = kwargs["harness_runtime_profile"]
        transcript_file = pathlib.Path(
            harness_runtime_profile.render_session_transcript_path(
                session_identifier, str(workspace_directory)
            )
        )
        transcript_file.parent.mkdir(parents=True, exist_ok=True)
        transcript_file.write_text("")
        begin_harness_productivity_record(record_path, "claude")
        baseline_next_delivery(record_path, session_identifier, 0)
        return (0.0, False, False)

    monkeypatch.setattr(
        launch_iterations,
        "run_launch_command_once",
        fake_run_launch_command_once,
    )
    monkeypatch.setattr(
        wrapper,
        "is_within_active_hours",
        lambda start, end, now=None, active_weekdays_only=False: True,
    )
    monkeypatch.setattr(wrapper.time, "sleep", lambda seconds: None)
    monkeypatch.setitem(
        launch_iterations.decide_and_persist_launch_session.__globals__,
        "session_conversation_exists",
        lambda _profile, _identifier, _workspace_directory=None: True,
    )

    with pytest.raises(StopSupervising):
        wrapper.supervise_agent_forever("steward", str(config_file))

    assert launch_commands_run == ["claude", "claude", "claude", "codex"]
