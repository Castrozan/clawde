import json
import pathlib

import channel_turn_harness
from active_harness import override_file_path_for_agent
from harness_productivity_record import (
    harness_productivity_record_path,
    read_harness_productivity_record,
)

AGENT_NAME = "silver"

LAUNCH_CONFIG = {
    "declared_harness": "claude",
    "harness_launch_commands": {
        "claude": "claude",
        "codex": "codex",
        "opencode": "opencode",
    },
    "harness_one_shot_turn_commands": {
        "claude": "claude-one-shot",
        "codex": "codex-one-shot",
        "opencode": "opencode-one-shot",
    },
}


def deploy_launch_config(tmp_path, launch_config):
    launch_config_directory = tmp_path / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    launch_config_path = launch_config_directory / f"{AGENT_NAME}.json"
    launch_config_path.write_text(json.dumps(launch_config))
    return str(launch_config_path)


def write_harness_override(tmp_path, harness_name):
    override_path = pathlib.Path(
        override_file_path_for_agent(str(tmp_path), AGENT_NAME)
    )
    override_path.parent.mkdir(parents=True, exist_ok=True)
    override_path.write_text(json.dumps({"harness": harness_name}))
    return str(override_path)


def test_resolution_uses_the_declared_harness_without_an_override(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, LAUNCH_CONFIG)
    harness_name, command = channel_turn_harness.resolve_active_one_shot_turn_command(
        launch_config_path
    )
    assert harness_name == "claude"
    assert command == "claude-one-shot"


def test_resolution_follows_a_runtime_harness_override(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, LAUNCH_CONFIG)
    write_harness_override(tmp_path, "opencode")
    harness_name, command = channel_turn_harness.resolve_active_one_shot_turn_command(
        launch_config_path
    )
    assert harness_name == "opencode"
    assert command == "opencode-one-shot"


def test_a_harness_without_a_one_shot_command_resolves_to_none(tmp_path):
    launch_config_path = deploy_launch_config(
        tmp_path,
        {
            **LAUNCH_CONFIG,
            "harness_one_shot_turn_commands": {"claude": "claude-one-shot"},
        },
    )
    write_harness_override(tmp_path, "opencode")
    harness_name, command = channel_turn_harness.resolve_active_one_shot_turn_command(
        launch_config_path
    )
    assert harness_name == "opencode"
    assert command is None


def test_productivity_record_tracks_turns_against_the_active_harness(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, LAUNCH_CONFIG)
    record_path = harness_productivity_record_path(str(tmp_path), AGENT_NAME)
    channel_turn_harness.record_channel_turn_productivity(
        launch_config_path, AGENT_NAME, "claude", turn_was_productive=True
    )
    assert read_harness_productivity_record(str(record_path))["harness"] == "claude"
    assert (
        read_harness_productivity_record(str(record_path))[
            "consecutive_unproductive_turns"
        ]
        == 0
    )
    channel_turn_harness.record_channel_turn_productivity(
        launch_config_path, AGENT_NAME, "claude", turn_was_productive=False
    )
    assert (
        read_harness_productivity_record(str(record_path))[
            "consecutive_unproductive_turns"
        ]
        == 1
    )


def test_productivity_record_rebegins_when_the_active_harness_changes(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, LAUNCH_CONFIG)
    record_path = harness_productivity_record_path(str(tmp_path), AGENT_NAME)
    channel_turn_harness.record_channel_turn_productivity(
        launch_config_path, AGENT_NAME, "claude", turn_was_productive=False
    )
    channel_turn_harness.record_channel_turn_productivity(
        launch_config_path, AGENT_NAME, "claude", turn_was_productive=False
    )
    channel_turn_harness.record_channel_turn_productivity(
        launch_config_path, AGENT_NAME, "opencode", turn_was_productive=True
    )
    record = read_harness_productivity_record(str(record_path))
    assert record["harness"] == "opencode"
    assert record["consecutive_unproductive_turns"] == 0
