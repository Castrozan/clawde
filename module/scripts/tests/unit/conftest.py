import pathlib
import sys

import pytest

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service")
)
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)


@pytest.fixture(autouse=True)
def agent_runtime_state_is_isolated_from_this_machines_live_agents(
    tmp_path, monkeypatch
):
    isolated_home_directory = tmp_path / "isolated-home"
    isolated_home_directory.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(isolated_home_directory))
