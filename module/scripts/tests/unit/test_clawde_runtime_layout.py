import importlib.util
import json
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)
sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))


def _load_clawde_runtime_layout_module():
    module_spec = importlib.util.spec_from_file_location(
        "clawde_runtime_layout", AGENT_WRAPPER_DIRECTORY / "clawde_runtime_layout.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


clawde_runtime_layout = _load_clawde_runtime_layout_module()


def test_runtime_root_directory_is_clawde_under_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert clawde_runtime_layout.runtime_root_directory() == str(tmp_path / "clawde")


def test_launch_config_path_for_agent_is_under_launch_config_directory(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert clawde_runtime_layout.launch_config_path_for_agent("steward") == str(
        tmp_path / "clawde" / "launch-config" / "steward.json"
    )


def test_deployed_agent_names_lists_sorted_json_basenames(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    launch_config_directory = tmp_path / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True)
    (launch_config_directory / "steward.json").write_text("{}")
    (launch_config_directory / "betha-pm.json").write_text("{}")
    (launch_config_directory / "notes.txt").write_text("ignored")
    assert clawde_runtime_layout.deployed_agent_names() == ["betha-pm", "steward"]


def test_deployed_agent_names_is_empty_when_directory_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert clawde_runtime_layout.deployed_agent_names() == []


def test_read_active_hours_window_returns_start_and_end(tmp_path):
    launch_config_path = tmp_path / "steward.json"
    launch_config_path.write_text(
        json.dumps({"active_hours_start": 8, "active_hours_end": 20})
    )
    assert clawde_runtime_layout.read_active_hours_window(str(launch_config_path)) == (
        8,
        20,
    )


def test_read_active_hours_window_returns_none_for_missing_fields(tmp_path):
    launch_config_path = tmp_path / "steward.json"
    launch_config_path.write_text("{}")
    assert clawde_runtime_layout.read_active_hours_window(str(launch_config_path)) == (
        None,
        None,
    )
