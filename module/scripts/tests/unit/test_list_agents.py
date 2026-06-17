import datetime
import importlib.util
import json
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)
sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))


def _load_list_agents_module():
    module_spec = importlib.util.spec_from_file_location(
        "list_agents", AGENT_WRAPPER_DIRECTORY / "list_agents.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


list_agents = _load_list_agents_module()


def test_describe_active_hours_window_formats_gated_window():
    assert list_agents.describe_active_hours_window(8, 20) == "08:00-20:00"


def test_describe_active_hours_window_is_always_on_when_ungated():
    assert list_agents.describe_active_hours_window(None, None) == "always-on"


def test_describe_override_status_reports_none_active_and_expired():
    now = datetime.datetime(2026, 6, 16, 22, 0, 0)
    future = datetime.datetime(2026, 6, 17, 8, 0, 0)
    past = datetime.datetime(2026, 6, 16, 8, 0, 0)
    assert list_agents.describe_override_status(None, now) == "none"
    assert (
        list_agents.describe_override_status(future, now)
        == "active until 2026-06-17T08:00:00"
    )
    assert list_agents.describe_override_status(past, now) == "expired"


def test_format_agent_rows_aligns_columns_and_includes_header():
    agent_rows = [
        {
            "agent": "ai-first-initiative",
            "active_hours": "08:00-20:00",
            "override": "none",
        },
        {
            "agent": "steward",
            "active_hours": "always-on",
            "override": "active until 2026-06-17T08:00:00",
        },
    ]
    lines = list_agents.format_agent_rows(agent_rows).split("\n")
    assert lines[0] == (
        "AGENT".ljust(19) + "  " + "ACTIVE HOURS".ljust(12) + "  " + "OVERRIDE"
    )
    assert lines[1] == (
        "ai-first-initiative".ljust(19) + "  " + "08:00-20:00".ljust(12) + "  " + "none"
    )
    assert lines[2] == (
        "steward".ljust(19)
        + "  "
        + "always-on".ljust(12)
        + "  "
        + "active until 2026-06-17T08:00:00"
    )


def test_collect_agent_rows_reads_hours_and_override(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    launch_config_directory = tmp_path / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True)
    (launch_config_directory / "ai-first-initiative.json").write_text(
        json.dumps({"active_hours_start": 8, "active_hours_end": 20})
    )
    (launch_config_directory / "steward.json").write_text(json.dumps({}))
    override_directory = tmp_path / "clawde" / "active-hours-override"
    override_directory.mkdir(parents=True)
    (override_directory / "ai-first-initiative.json").write_text(
        json.dumps({"active_until": "2026-06-17T08:00:00"})
    )

    agent_rows = list_agents.collect_agent_rows(
        datetime.datetime(2026, 6, 16, 22, 0, 0)
    )

    assert agent_rows == [
        {
            "agent": "ai-first-initiative",
            "active_hours": "08:00-20:00",
            "override": "active until 2026-06-17T08:00:00",
        },
        {"agent": "steward", "active_hours": "always-on", "override": "none"},
    ]


def test_collect_agent_rows_marks_unreadable_launch_config(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    launch_config_directory = tmp_path / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True)
    (launch_config_directory / "steward.json").write_text("not json{{{")

    agent_rows = list_agents.collect_agent_rows(
        datetime.datetime(2026, 6, 16, 22, 0, 0)
    )

    assert agent_rows == [
        {"agent": "steward", "active_hours": "unreadable", "override": "none"}
    ]


def test_format_agent_rows_with_no_agents_returns_header_line_only():
    assert list_agents.format_agent_rows([]) == "AGENT  ACTIVE HOURS  OVERRIDE"
