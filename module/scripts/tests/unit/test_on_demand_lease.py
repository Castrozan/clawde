import datetime
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import on_demand_lease


def test_lease_file_path_lives_under_the_on_demand_subdirectory():
    assert (
        on_demand_lease.lease_file_path_for_agent("/runtime", "betha")
        == "/runtime/on-demand/betha.json"
    )


def test_written_lease_reads_back_as_the_same_moment(tmp_path):
    lease_file_path = str(tmp_path / "on-demand" / "agent.json")
    started_at = datetime.datetime(2026, 7, 20, 9, 30, 0)

    on_demand_lease.write_lease_started_at(lease_file_path, started_at)

    assert on_demand_lease.read_lease_started_at(lease_file_path) == started_at


def test_missing_lease_reads_as_none(tmp_path):
    assert on_demand_lease.read_lease_started_at(str(tmp_path / "absent.json")) is None


def test_malformed_lease_reads_as_none(tmp_path):
    lease_file_path = tmp_path / "agent.json"
    lease_file_path.write_text("not json{{{")

    assert on_demand_lease.read_lease_started_at(str(lease_file_path)) is None


def test_lease_without_a_started_at_key_reads_as_none(tmp_path):
    lease_file_path = tmp_path / "agent.json"
    lease_file_path.write_text('{"something_else": 1}')

    assert on_demand_lease.read_lease_started_at(str(lease_file_path)) is None


def test_clearing_an_absent_lease_is_not_an_error(tmp_path):
    on_demand_lease.clear_lease(str(tmp_path / "absent.json"))


def test_cleared_lease_stops_reading_back(tmp_path):
    lease_file_path = str(tmp_path / "on-demand" / "agent.json")
    on_demand_lease.write_lease_started_at(
        lease_file_path, datetime.datetime(2026, 7, 20, 9, 30, 0)
    )

    on_demand_lease.clear_lease(lease_file_path)

    assert on_demand_lease.read_lease_started_at(lease_file_path) is None


def test_latest_activity_falls_back_to_the_lease_start_without_a_transcript():
    lease_started_at = datetime.datetime(2026, 7, 20, 9, 30, 0)

    assert (
        on_demand_lease.latest_activity_time(lease_started_at, None) == lease_started_at
    )


def test_latest_activity_ignores_a_transcript_older_than_the_lease_start():
    lease_started_at = datetime.datetime(2026, 7, 20, 9, 30, 0)
    stale_transcript_time = datetime.datetime(2026, 7, 18, 14, 0, 0)

    assert (
        on_demand_lease.latest_activity_time(lease_started_at, stale_transcript_time)
        == lease_started_at
    )


def test_latest_activity_takes_a_transcript_newer_than_the_lease_start():
    lease_started_at = datetime.datetime(2026, 7, 20, 9, 30, 0)
    fresh_transcript_time = datetime.datetime(2026, 7, 20, 10, 15, 0)

    assert (
        on_demand_lease.latest_activity_time(lease_started_at, fresh_transcript_time)
        == fresh_transcript_time
    )


def test_lease_is_not_idle_before_the_timeout_elapses():
    latest_activity_at = datetime.datetime(2026, 7, 20, 9, 30, 0)
    now = datetime.datetime(2026, 7, 20, 9, 59, 0)

    assert not on_demand_lease.lease_has_gone_idle(latest_activity_at, 30, now)


def test_lease_is_idle_once_the_timeout_has_elapsed():
    latest_activity_at = datetime.datetime(2026, 7, 20, 9, 30, 0)
    now = datetime.datetime(2026, 7, 20, 10, 0, 0)

    assert on_demand_lease.lease_has_gone_idle(latest_activity_at, 30, now)
