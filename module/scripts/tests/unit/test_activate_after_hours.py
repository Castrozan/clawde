import datetime
import importlib.util
import json
import pathlib
import signal
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)
sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))


def _load_activate_after_hours_module():
    module_spec = importlib.util.spec_from_file_location(
        "activate_after_hours", AGENT_WRAPPER_DIRECTORY / "activate_after_hours.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


activate_after_hours = _load_activate_after_hours_module()


class _CompletedProcess:
    def __init__(self, stdout):
        self.stdout = stdout


def _write_launch_config(home_directory, agent_name, active_hours_start):
    launch_config_path = (
        home_directory / "clawde" / "launch-config" / f"{agent_name}.json"
    )
    launch_config_path.parent.mkdir(parents=True, exist_ok=True)
    launch_config_path.write_text(
        json.dumps({"active_hours_start": active_hours_start})
    )
    return launch_config_path


def test_find_agent_wrapper_process_ids_parses_pgrep_output(monkeypatch):
    monkeypatch.setattr(
        activate_after_hours.subprocess,
        "run",
        lambda *_args, **_kwargs: _CompletedProcess("123\n456\n"),
    )
    assert activate_after_hours.find_agent_wrapper_process_ids("steward") == [123, 456]


def test_signal_agent_wrapper_to_restart_sends_sigterm_to_each_process(monkeypatch):
    monkeypatch.setattr(
        activate_after_hours,
        "find_agent_wrapper_process_ids",
        lambda agent_name: [123, 456],
    )
    signalled = []
    monkeypatch.setattr(
        activate_after_hours.os,
        "kill",
        lambda process_id, sent_signal: signalled.append((process_id, sent_signal)),
    )
    assert activate_after_hours.signal_agent_wrapper_to_restart("steward") == 2
    assert signalled == [(123, signal.SIGTERM), (456, signal.SIGTERM)]


def test_set_active_hours_override_writes_next_start_and_signals(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(tmp_path, "steward", 8)
    monkeypatch.setattr(
        activate_after_hours, "find_agent_wrapper_process_ids", lambda agent_name: []
    )

    now_after_hours = datetime.datetime(2026, 6, 16, 22, 0, 0)
    activate_after_hours.set_active_hours_override("steward", now_after_hours)

    override_file = tmp_path / "clawde" / "active-hours-override" / "steward.json"
    assert json.loads(override_file.read_text()) == {
        "active_until": "2026-06-17T08:00:00"
    }


def test_set_active_hours_override_is_noop_when_no_active_hours_gate(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_launch_config(tmp_path, "steward", None)
    monkeypatch.setattr(
        activate_after_hours, "find_agent_wrapper_process_ids", lambda agent_name: []
    )

    activate_after_hours.set_active_hours_override(
        "steward", datetime.datetime(2026, 6, 16, 22, 0, 0)
    )

    override_file = tmp_path / "clawde" / "active-hours-override" / "steward.json"
    assert not override_file.exists()


def test_clear_active_hours_override_removes_file_and_signals(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    override_file = tmp_path / "clawde" / "active-hours-override" / "steward.json"
    override_file.parent.mkdir(parents=True, exist_ok=True)
    override_file.write_text(json.dumps({"active_until": "2026-06-17T08:00:00"}))
    monkeypatch.setattr(
        activate_after_hours, "find_agent_wrapper_process_ids", lambda agent_name: []
    )

    activate_after_hours.clear_active_hours_override("steward")

    assert not override_file.exists()
