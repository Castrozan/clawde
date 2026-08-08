import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

import clawde_cli

AGENT_WRAPPER_DIRECTORY = "/nix/store/agent-wrapper"


@pytest.fixture(autouse=True)
def clawde_cli_runtime_configuration(monkeypatch):
    monkeypatch.setenv("CLAWDE_AGENT_WRAPPER_DIR", AGENT_WRAPPER_DIRECTORY)


@pytest.fixture
def dispatched_arguments(monkeypatch):
    recorded_arguments: list[list[str]] = []
    monkeypatch.setattr(
        "os.execvpe",
        lambda executable, arguments, environment: recorded_arguments.append(arguments),
    )
    return recorded_arguments


def test_restart_dispatch_drops_the_subcommand_word(dispatched_arguments):
    assert clawde_cli.main(["restart", "monster"]) == 0

    assert dispatched_arguments == [
        [
            sys.executable,
            f"{AGENT_WRAPPER_DIRECTORY}/restart_agent.py",
            "monster",
        ]
    ]


def test_usage_documents_restart_and_why_it_exists(capsys):
    assert clawde_cli.main(["--help"]) == 0

    printed_usage = capsys.readouterr().out
    assert "restart" in printed_usage
    assert "new wrapper code" in printed_usage
