import os
import pathlib
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

import clawde_cli

AGENT_WRAPPER_DIRECTORY = "/nix/store/agent-wrapper"
TMUX_BIN_PATH = "/nix/store/tmux/bin/tmux"
DEFAULT_SESSION_NAME = "clawde"
SYSTEMD_RESTART_COMMAND = "systemctl --user restart clawde"


@pytest.fixture(autouse=True)
def clawde_cli_runtime_configuration(monkeypatch):
    monkeypatch.setenv("CLAWDE_AGENT_WRAPPER_DIR", AGENT_WRAPPER_DIRECTORY)
    monkeypatch.setenv("TMUX_BIN", TMUX_BIN_PATH)
    monkeypatch.setenv("DEFAULT_TMUX_SESSION_NAME", DEFAULT_SESSION_NAME)
    monkeypatch.setenv("CLAWDE_SERVICE_RESTART_COMMAND", SYSTEMD_RESTART_COMMAND)


@pytest.fixture
def external_commands_are_forbidden(monkeypatch):
    def fail_external_command(*arguments, **keyword_arguments):
        raise AssertionError(
            "this CLI path must not run external commands, got "
            f"arguments={arguments!r} keyword_arguments={keyword_arguments!r}"
        )

    monkeypatch.setattr("os.execvpe", fail_external_command)
    monkeypatch.setattr("subprocess.run", fail_external_command)


@pytest.fixture
def recorded_subprocess_commands(monkeypatch):
    recorded_commands = []

    def record_subprocess_command(command, **keyword_arguments):
        recorded_commands.append(command)
        return types.SimpleNamespace(returncode=1)

    monkeypatch.setattr("subprocess.run", record_subprocess_command)
    return recorded_commands


def run_clawde_cli(arguments):
    return clawde_cli.main(arguments)


def test_every_help_form_prints_usage_without_side_effects(capsys):
    for help_argument in ["--help", "-h", "help"]:
        exit_code = run_clawde_cli([help_argument])
        printed_usage = capsys.readouterr()
        assert exit_code == 0
        assert printed_usage.err == ""
        assert "usage: clawde" in printed_usage.out


def test_usage_names_every_supported_command_and_its_purpose(capsys):
    run_clawde_cli(["--help"])
    printed_usage = capsys.readouterr().out

    assert "active" in printed_usage
    assert "active-hours gate" in printed_usage
    assert "harness" in printed_usage
    assert "list" in printed_usage
    assert "on-demand" in printed_usage
    assert "start" in printed_usage
    assert "stop" in printed_usage
    assert "help" in printed_usage
    assert "preserving" in printed_usage


def test_help_forms_never_probe_the_multiplexer_or_restart_a_service(
    external_commands_are_forbidden, capsys
):
    for help_argument in ["--help", "-h", "help"]:
        assert run_clawde_cli([help_argument]) == 0
        capsys.readouterr()


def test_unknown_command_exits_nonzero_without_side_effects(
    external_commands_are_forbidden, capsys
):
    exit_code = run_clawde_cli(["frobnicate"])

    printed_usage = capsys.readouterr()
    assert exit_code == 2
    assert "frobnicate" in printed_usage.err
    assert "usage: clawde" in printed_usage.err
    assert printed_usage.out == ""


def test_unknown_flag_exits_nonzero_without_side_effects(
    external_commands_are_forbidden, capsys
):
    exit_code = run_clawde_cli(["--frobnicate"])

    printed_usage = capsys.readouterr()
    assert exit_code == 2
    assert "usage: clawde" in printed_usage.err
    assert printed_usage.out == ""


def test_active_dispatch_drops_the_subcommand_word(monkeypatch, capsys):
    dispatched_arguments = []
    monkeypatch.setattr(
        "os.execvpe",
        lambda executable, arguments, environment: dispatched_arguments.append(
            arguments
        ),
    )

    assert run_clawde_cli(["active", "--clear", "agent-x"]) == 0

    assert dispatched_arguments == [
        [
            sys.executable,
            f"{AGENT_WRAPPER_DIRECTORY}/activate_after_hours.py",
            "--clear",
            "agent-x",
        ]
    ]
    capsys.readouterr()


def test_list_dispatch_drops_the_subcommand_word(monkeypatch):
    dispatched_arguments = []
    monkeypatch.setattr(
        "os.execvpe",
        lambda executable, arguments, environment: dispatched_arguments.append(
            arguments
        ),
    )

    assert run_clawde_cli(["list", "--flag"]) == 0

    assert dispatched_arguments == [
        [sys.executable, f"{AGENT_WRAPPER_DIRECTORY}/list_agents.py", "--flag"]
    ]


def test_harness_dispatch_drops_the_subcommand_word(monkeypatch):
    dispatched_arguments = []
    monkeypatch.setattr(
        "os.execvpe",
        lambda executable, arguments, environment: dispatched_arguments.append(
            arguments
        ),
    )

    assert run_clawde_cli(["harness", "agent-x", "--eligible"]) == 0

    assert dispatched_arguments == [
        [
            sys.executable,
            f"{AGENT_WRAPPER_DIRECTORY}/harness_control.py",
            "agent-x",
            "--eligible",
        ]
    ]


def test_start_dispatch_keeps_the_subcommand_word(monkeypatch):
    dispatched_arguments = []
    monkeypatch.setattr(
        "os.execvpe",
        lambda executable, arguments, environment: dispatched_arguments.append(
            arguments
        ),
    )

    assert run_clawde_cli(["start", "agent-x"]) == 0

    assert dispatched_arguments == [
        [
            sys.executable,
            f"{AGENT_WRAPPER_DIRECTORY}/on_demand_control.py",
            "start",
            "agent-x",
        ]
    ]


def test_stop_dispatch_keeps_the_subcommand_word(monkeypatch):
    dispatched_arguments = []
    monkeypatch.setattr(
        "os.execvpe",
        lambda executable, arguments, environment: dispatched_arguments.append(
            arguments
        ),
    )

    assert run_clawde_cli(["stop", "agent-x"]) == 0

    assert dispatched_arguments == [
        [
            sys.executable,
            f"{AGENT_WRAPPER_DIRECTORY}/on_demand_control.py",
            "stop",
            "agent-x",
        ]
    ]


def test_no_argument_startup_restarts_the_injected_service_when_the_session_is_absent(
    recorded_subprocess_commands, capsys
):
    assert run_clawde_cli([]) == 1

    assert recorded_subprocess_commands == [
        [TMUX_BIN_PATH, "has-session", "-t", DEFAULT_SESSION_NAME],
        ["systemctl", "--user", "restart", "clawde"],
    ]
    assert capsys.readouterr().out == ""


def test_no_argument_startup_reports_when_the_session_is_already_running(
    monkeypatch, capsys
):
    recorded_commands = []

    def run_and_report_session_present(command, **keyword_arguments):
        recorded_commands.append(command)
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr("subprocess.run", run_and_report_session_present)

    assert run_clawde_cli([]) == 0

    assert recorded_commands == [
        [TMUX_BIN_PATH, "has-session", "-t", DEFAULT_SESSION_NAME]
    ]
    printed_message = capsys.readouterr()
    assert f"Session {DEFAULT_SESSION_NAME} already running" in printed_message.err


def test_no_argument_startup_substitutes_the_uid_into_the_launchd_restart_command(
    monkeypatch, recorded_subprocess_commands
):
    monkeypatch.setenv(
        "CLAWDE_SERVICE_RESTART_COMMAND",
        "launchctl kickstart -k gui/UID/org.nix-community.home.clawde",
    )

    assert run_clawde_cli([]) == 1

    assert recorded_subprocess_commands == [
        [TMUX_BIN_PATH, "has-session", "-t", DEFAULT_SESSION_NAME],
        [
            "launchctl",
            "kickstart",
            "-k",
            f"gui/{os.getuid()}/org.nix-community.home.clawde",
        ],
    ]
