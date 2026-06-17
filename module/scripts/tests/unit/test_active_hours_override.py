import datetime
import importlib.util
import pathlib
import sys


def _load_active_hours_override_module():
    module_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "agent-wrapper"
        / "active_hours_override.py"
    )
    module_spec = importlib.util.spec_from_file_location(
        "active_hours_override", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["active_hours_override"] = module
    module_spec.loader.exec_module(module)
    return module


active_hours_override = _load_active_hours_override_module()


def test_runtime_root_directory_is_grandparent_of_launch_config():
    assert (
        active_hours_override.runtime_root_directory_from_launch_config_path(
            "/home/u/clawde/launch-config/steward.json"
        )
        == "/home/u/clawde"
    )


def test_override_file_path_for_agent_is_under_override_subdirectory():
    assert (
        active_hours_override.override_file_path_for_agent("/home/u/clawde", "steward")
        == "/home/u/clawde/active-hours-override/steward.json"
    )


def test_write_then_read_round_trips_the_active_until(tmp_path):
    override_file = str(tmp_path / "override" / "steward.json")
    active_until = datetime.datetime(2026, 6, 17, 8, 0, 0)
    active_hours_override.write_override_active_until(override_file, active_until)
    assert (
        active_hours_override.read_override_active_until(override_file) == active_until
    )


def test_read_returns_none_when_file_missing(tmp_path):
    assert (
        active_hours_override.read_override_active_until(str(tmp_path / "absent.json"))
        is None
    )


def test_read_returns_none_when_file_corrupt(tmp_path):
    override_file = tmp_path / "override.json"
    override_file.write_text("not json")
    assert active_hours_override.read_override_active_until(str(override_file)) is None


def test_read_returns_none_when_key_absent(tmp_path):
    override_file = tmp_path / "override.json"
    override_file.write_text("{}")
    assert active_hours_override.read_override_active_until(str(override_file)) is None


def test_clear_override_is_silent_when_file_missing(tmp_path):
    active_hours_override.clear_override(str(tmp_path / "absent.json"))


def test_clear_override_removes_existing_file(tmp_path):
    override_file = tmp_path / "override.json"
    override_file.write_text("{}")
    active_hours_override.clear_override(str(override_file))
    assert not override_file.exists()


def test_is_override_active_true_for_future():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    future = datetime.datetime(2026, 6, 17, 8, 0, 0)
    assert active_hours_override.is_override_active(future, now) is True


def test_is_override_active_false_for_past_and_none():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    past = datetime.datetime(2026, 6, 16, 8, 0, 0)
    assert active_hours_override.is_override_active(past, now) is False
    assert active_hours_override.is_override_active(None, now) is False


def test_active_hours_gate_allows_run_when_within_hours_even_without_override():
    now = datetime.datetime(2026, 6, 16, 12, 0, 0)
    assert active_hours_override.active_hours_gate_allows_run(True, None, now) is True


def test_active_hours_gate_allows_run_outside_hours_only_with_active_override():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    future = datetime.datetime(2026, 6, 17, 8, 0, 0)
    assert (
        active_hours_override.active_hours_gate_allows_run(False, future, now) is True
    )
    assert active_hours_override.active_hours_gate_allows_run(False, None, now) is False


def test_override_is_stale_false_when_no_override():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    assert active_hours_override.override_is_stale(False, None, now) is False


def test_override_is_stale_true_within_hours():
    now = datetime.datetime(2026, 6, 16, 12, 0, 0)
    future = datetime.datetime(2026, 6, 17, 8, 0, 0)
    assert active_hours_override.override_is_stale(True, future, now) is True


def test_override_is_stale_true_when_expired_outside_hours():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    past = datetime.datetime(2026, 6, 16, 8, 0, 0)
    assert active_hours_override.override_is_stale(False, past, now) is True


def test_override_is_stale_false_when_active_outside_hours():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    future = datetime.datetime(2026, 6, 17, 8, 0, 0)
    assert active_hours_override.override_is_stale(False, future, now) is False
