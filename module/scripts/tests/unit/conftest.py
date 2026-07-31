import os
import pathlib
import sys

import pytest

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service")
)
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)
sys.path.insert(
    0,
    str(
        pathlib.Path(__file__).resolve().parent.parent.parent.parent
        / "channel-adapters"
        / "discord"
        / "scripts"
    ),
)


@pytest.fixture(autouse=True)
def agent_runtime_state_is_isolated_from_this_machines_live_agents(
    tmp_path, monkeypatch
):
    isolated_home_directory = tmp_path / "isolated-home"
    isolated_home_directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(isolated_home_directory))
    monkeypatch.delenv("CLAWDE_MULTIPLEXER", raising=False)


@pytest.fixture(autouse=True)
def process_lookups_are_isolated_from_this_machines_live_processes(
    tmp_path, monkeypatch
):
    process_lookup_stub_directory = tmp_path / "process-lookup-stubs"
    process_lookup_stub_directory.mkdir(parents=True, exist_ok=True)
    no_match_pgrep_path = process_lookup_stub_directory / "pgrep"
    no_match_pgrep_path.write_text(f"#!{sys.executable}\nraise SystemExit(1)\n")
    no_match_pgrep_path.chmod(0o755)
    monkeypatch.setenv(
        "PATH", f"{process_lookup_stub_directory}{os.pathsep}{os.environ['PATH']}"
    )
