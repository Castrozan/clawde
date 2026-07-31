import json
import pathlib

import active_harness
import pytest
from harness_profile_test_helpers import (
    CLAUDE_PROFILE_MAPPING,
    CODEX_PROFILE_MAPPING,
)
from harness_runtime_profile import load_harness_runtime_profile_from_launch_config

AGENT_NAME = "steward"


def two_harness_launch_config():
    return {
        "declared_harness": "claude",
        "harness_launch_commands": {"claude": "claude --x", "codex": "codex --y"},
        "harness_runtime_profiles": {
            "claude": CLAUDE_PROFILE_MAPPING,
            "codex": CODEX_PROFILE_MAPPING,
        },
    }


def deploy_launch_config(runtime_root_directory, launch_config):
    launch_config_directory = runtime_root_directory / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    launch_config_path = launch_config_directory / f"{AGENT_NAME}.json"
    launch_config_path.write_text(json.dumps(launch_config))
    return str(launch_config_path)


def test_eligible_harness_names_are_the_materialized_launch_commands():
    assert active_harness.eligible_harness_names(two_harness_launch_config()) == [
        "claude",
        "codex",
    ]


def test_absent_override_resolves_to_the_declared_harness(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, two_harness_launch_config())
    assert (
        active_harness.active_harness_name_for_launch_config(
            two_harness_launch_config(), launch_config_path
        )
        == "claude"
    )


def test_override_moves_the_agent_onto_the_other_harness(tmp_path):
    launch_config = two_harness_launch_config()
    launch_config_path = deploy_launch_config(tmp_path, launch_config)
    active_harness.write_overridden_harness_name(
        active_harness.override_file_path_for_agent(str(tmp_path), AGENT_NAME), "codex"
    )
    assert (
        active_harness.active_harness_name_for_launch_config(
            launch_config, launch_config_path
        )
        == "codex"
    )
    assert active_harness.active_launch_command(launch_config, "codex") == "codex --y"


def test_override_naming_an_unmaterialized_harness_falls_back_to_declared(tmp_path):
    launch_config = two_harness_launch_config()
    launch_config_path = deploy_launch_config(tmp_path, launch_config)
    active_harness.write_overridden_harness_name(
        active_harness.override_file_path_for_agent(str(tmp_path), AGENT_NAME),
        "opencode",
    )
    assert (
        active_harness.active_harness_name_for_launch_config(
            launch_config, launch_config_path
        )
        == "claude"
    )


def test_cleared_override_returns_the_agent_to_its_declared_harness(tmp_path):
    launch_config = two_harness_launch_config()
    launch_config_path = deploy_launch_config(tmp_path, launch_config)
    override_file_path = active_harness.override_file_path_for_agent(
        str(tmp_path), AGENT_NAME
    )
    active_harness.write_overridden_harness_name(override_file_path, "codex")
    active_harness.clear_override(override_file_path)
    assert (
        active_harness.active_harness_name_for_launch_config(
            launch_config, launch_config_path
        )
        == "claude"
    )


def test_a_corrupt_override_file_does_not_break_resolution(tmp_path):
    launch_config = two_harness_launch_config()
    launch_config_path = deploy_launch_config(tmp_path, launch_config)
    override_file_path = active_harness.override_file_path_for_agent(
        str(tmp_path), AGENT_NAME
    )
    pathlib.Path(override_file_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(override_file_path).write_text("{not json")
    assert (
        active_harness.active_harness_name_for_launch_config(
            launch_config, launch_config_path
        )
        == "claude"
    )


def test_the_runtime_profile_loader_follows_the_override(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, two_harness_launch_config())
    assert (
        load_harness_runtime_profile_from_launch_config(launch_config_path).harness_name
        == "claude"
    )
    active_harness.write_overridden_harness_name(
        active_harness.override_file_path_for_agent(str(tmp_path), AGENT_NAME), "codex"
    )
    assert (
        load_harness_runtime_profile_from_launch_config(launch_config_path).harness_name
        == "codex"
    )


@pytest.mark.parametrize(
    "launch_config_path, expected_agent_name",
    [
        ("/home/someone/clawde/launch-config/steward.json", "steward"),
        ("/home/someone/clawde/launch-config/pm-bot.json", "pm-bot"),
    ],
)
def test_agent_name_comes_from_the_launch_config_file_name(
    launch_config_path, expected_agent_name
):
    assert (
        active_harness.agent_name_from_launch_config_path(launch_config_path)
        == expected_agent_name
    )
