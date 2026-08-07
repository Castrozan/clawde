import json
import os
import pathlib

from harness_productivity_record import (
    begin_harness_productivity_record,
    consecutive_unproductive_turns,
    harness_productivity_record_path,
    read_harness_productivity_record,
)
from harness_profile_test_helpers import make_claude_profile
from heartbeat_test_support import load_heartbeat_module

heartbeat_turn_productivity = load_heartbeat_module("heartbeat_turn_productivity")

WORKSPACE_DIRECTORY = "/home/zanoni/clawde/steward"
WORKSPACE_TRANSCRIPT_SLUG = "-home-zanoni-clawde-steward"
SESSION_IDENTIFIER = "aa7e5857-08b4-4007-ac61-ff23b7d8dc1c"


class PaneNeverReportingWork:
    def pane_reports_active_work(self, _pane_handle):
        return False


class PaneReportingWork:
    def pane_reports_active_work(self, _pane_handle):
        return True


def write_live_session_identifier(runtime_root_directory, session_identifier):
    session_record_path = pathlib.Path(runtime_root_directory) / "session-ids"
    session_record_path.mkdir(parents=True, exist_ok=True)
    (session_record_path / "steward.json").write_text(
        json.dumps({"session_identifier": session_identifier})
    )


def build_parked_agent(tmp_path, initial_transcript_byte_size=4096):
    runtime_root_directory = str(tmp_path / "clawde")
    write_live_session_identifier(runtime_root_directory, SESSION_IDENTIFIER)
    transcript_directory = (
        pathlib.Path(os.environ["HOME"])
        / ".claude"
        / "projects"
        / WORKSPACE_TRANSCRIPT_SLUG
    )
    transcript_directory.mkdir(parents=True, exist_ok=True)
    transcript_file = transcript_directory / f"{SESSION_IDENTIFIER}.jsonl"
    transcript_file.write_bytes(b"x" * initial_transcript_byte_size)
    record_path = harness_productivity_record_path(runtime_root_directory, "steward")
    begin_harness_productivity_record(record_path, "claude")
    observer = heartbeat_turn_productivity.DeliveredTurnObserver(
        record_path,
        make_claude_profile(),
        runtime_root_directory,
        "steward",
        WORKSPACE_DIRECTORY,
    )
    return observer, record_path, transcript_file


def deliver_a_turn(observer, backend, transcript_file, bytes_written_by_the_turn):
    observer.judge_previous_delivery()
    observer.observe_this_delivery(backend, "pane-handle", lambda _seconds: None)
    if bytes_written_by_the_turn:
        with open(transcript_file, "ab") as open_transcript_file:
            open_transcript_file.write(b"y" * bytes_written_by_the_turn)


def counted_unproductive_turns(record_path):
    return consecutive_unproductive_turns(read_harness_productivity_record(record_path))


def test_a_transcript_that_grew_between_deliveries_counts_as_work(tmp_path):
    observer, record_path, transcript_file = build_parked_agent(tmp_path)
    for _ in range(3):
        deliver_a_turn(observer, PaneNeverReportingWork(), transcript_file, 8192)
    assert counted_unproductive_turns(record_path) == 0


def test_a_transcript_that_never_grew_counts_as_no_work(tmp_path):
    observer, record_path, transcript_file = build_parked_agent(tmp_path)
    for _ in range(3):
        deliver_a_turn(observer, PaneNeverReportingWork(), transcript_file, 0)
    assert counted_unproductive_turns(record_path) == 2, (
        "a provider refusing the request leaves the session transcript exactly where "
        "the delivered prompt left it, which is the only on-disk difference between a "
        "quota-parked agent and a working one"
    )


def test_a_pane_that_reports_its_own_working_state_is_never_read_as_no_work(tmp_path):
    observer, record_path, transcript_file = build_parked_agent(tmp_path)
    for _ in range(3):
        deliver_a_turn(observer, PaneReportingWork(), transcript_file, 0)
    assert counted_unproductive_turns(record_path) == 0, (
        "a harness that reports working to the multiplexer is producing turns even "
        "when it keeps no transcript this observer can read"
    )


def test_a_harness_without_a_readable_transcript_is_never_read_as_no_work(tmp_path):
    observer, record_path, transcript_file = build_parked_agent(tmp_path)
    transcript_file.unlink()
    for _ in range(3):
        deliver_a_turn(observer, PaneNeverReportingWork(), transcript_file, 0)
    assert counted_unproductive_turns(record_path) == 0, (
        "missing evidence must not accumulate toward a failover, because moving a "
        "healthy agent off its harness is worse than missing every tick of evidence"
    )


def test_a_rotated_session_does_not_inherit_the_previous_sessions_measurement(tmp_path):
    observer, record_path, transcript_file = build_parked_agent(tmp_path)
    deliver_a_turn(observer, PaneNeverReportingWork(), transcript_file, 0)
    write_live_session_identifier(
        observer.runtime_root_directory, "a-newly-rotated-session"
    )
    deliver_a_turn(observer, PaneNeverReportingWork(), transcript_file, 0)
    assert counted_unproductive_turns(record_path) == 0, (
        "a relaunched session writes a different transcript, so its byte size can "
        "never be compared against the retired session's measurement"
    )
