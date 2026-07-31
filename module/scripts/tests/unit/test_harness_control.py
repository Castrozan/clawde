import json
import os
import pathlib

import harness_control
import pytest
from harness_profile_test_helpers import (
    CLAUDE_PROFILE_MAPPING,
    CODEX_PROFILE_MAPPING,
)

AGENT_NAME = "steward"


def deploy_agent(home_directory, declared_harness="claude"):
    launch_config_directory = home_directory / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    (launch_config_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(
            {
                "declared_harness": declared_harness,
                "harness_launch_commands": {
                    "claude": "claude --x",
                    "codex": "codex --y",
                },
                "harness_runtime_profiles": {
                    "claude": CLAUDE_PROFILE_MAPPING,
                    "codex": CODEX_PROFILE_MAPPING,
                },
            }
        )
    )


@pytest.fixture
def isolated_home():
    return pathlib.Path(os.environ["HOME"])


def test_showing_an_agent_reports_its_declared_harness(isolated_home, capsys):
    deploy_agent(isolated_home)
    harness_control.show_one_agent_harness(AGENT_NAME)
    printed = capsys.readouterr().out
    assert f"{AGENT_NAME}: claude" in printed
    assert "eligible: claude, codex" in printed


def test_switching_reports_the_new_harness_and_marks_the_override(
    isolated_home, capsys
):
    deploy_agent(isolated_home)
    harness_control.set_agent_harness(AGENT_NAME, "codex")
    assert "now runs on codex" in capsys.readouterr().out
    harness_control.show_one_agent_harness(AGENT_NAME)
    assert f"{AGENT_NAME}: codex (overriding claude)" in capsys.readouterr().out


def test_switching_to_an_ineligible_harness_is_refused(isolated_home):
    deploy_agent(isolated_home)
    with pytest.raises(SystemExit) as refusal:
        harness_control.set_agent_harness(AGENT_NAME, "opencode")
    assert "cannot run on harness 'opencode'" in str(refusal.value)


def test_clearing_returns_the_agent_to_its_declared_harness(isolated_home, capsys):
    deploy_agent(isolated_home)
    harness_control.set_agent_harness(AGENT_NAME, "codex")
    capsys.readouterr()
    harness_control.clear_agent_harness_override(AGENT_NAME)
    assert "returns to its declared harness claude" in capsys.readouterr().out
    harness_control.show_one_agent_harness(AGENT_NAME)
    assert f"{AGENT_NAME}: claude\n" in capsys.readouterr().out


def test_an_undeployed_agent_is_refused_with_the_deployed_names(isolated_home):
    deploy_agent(isolated_home)
    with pytest.raises(SystemExit) as refusal:
        harness_control.show_one_agent_harness("nobody")
    assert "has no deployed launch config" in str(refusal.value)
    assert AGENT_NAME in str(refusal.value)


def test_listing_every_agent_reports_one_line_each(isolated_home, capsys):
    deploy_agent(isolated_home)
    harness_control.show_every_agent_harness()
    assert capsys.readouterr().out.strip() == f"{AGENT_NAME}: claude"


def test_a_running_agent_is_signalled_to_restart(isolated_home, monkeypatch, capsys):
    deploy_agent(isolated_home)
    signalled_process_ids = []
    monkeypatch.setattr(
        harness_control, "find_wrapper_process_id_for_agent", lambda _agent_name: 4242
    )
    monkeypatch.setattr(
        harness_control.os,
        "kill",
        lambda process_id, _signal: signalled_process_ids.append(process_id),
    )
    harness_control.set_agent_harness(AGENT_NAME, "codex")
    assert signalled_process_ids == [4242]
    assert "signalled to restart" in capsys.readouterr().out
