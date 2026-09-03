import datetime

from harness_productivity_delivery import (
    baseline_next_delivery,
    judge_pending_delivery,
    judge_pending_delivery_after_session_exit,
)
from harness_productivity_record import (
    CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER,
    begin_harness_productivity_record,
    consecutive_unproductive_turns,
    harness_is_refusing_work,
    harness_productivity_record_path,
    read_harness_productivity_record,
    record_observed_heartbeat_turn,
)

AT_NOON = datetime.datetime(2026, 8, 7, 12, 0, 0)


def record_path(tmp_path, agent_name="steward"):
    return harness_productivity_record_path(str(tmp_path), agent_name)


def drive_unproductive_turns(path, turn_count):
    for _turn in range(turn_count):
        record_observed_heartbeat_turn(path, False, AT_NOON)
    return read_harness_productivity_record(path)


def test_a_missing_record_reads_as_an_empty_mapping(tmp_path):
    assert read_harness_productivity_record(record_path(tmp_path)) == {}


def test_a_corrupt_record_reads_as_an_empty_mapping(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode")
    with open(path, "w") as record_file:
        record_file.write("{not json")
    assert read_harness_productivity_record(path) == {}


def test_consecutive_unproductive_turns_accumulate(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    assert consecutive_unproductive_turns(drive_unproductive_turns(path, 2)) == 2


def test_one_productive_turn_clears_the_run(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    drive_unproductive_turns(path, CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER)
    record = record_observed_heartbeat_turn(path, True, AT_NOON)
    assert consecutive_unproductive_turns(record) == 0
    assert record["last_productive_turn_at"] == AT_NOON.isoformat()


def test_a_harness_is_refusing_work_only_at_the_threshold(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    drive_unproductive_turns(path, CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER - 1)
    assert (
        harness_is_refusing_work(read_harness_productivity_record(path), "opencode")
        is False
    )
    record_observed_heartbeat_turn(path, False, AT_NOON)
    assert (
        harness_is_refusing_work(read_harness_productivity_record(path), "opencode")
        is True
    )


def test_a_run_recorded_against_another_harness_never_condemns_this_one(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    record = drive_unproductive_turns(
        path, CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER
    )
    assert harness_is_refusing_work(record, "codex") is False, (
        "the run belongs to the harness that was active while it accumulated; "
        "reading it against the harness the agent just moved to would fail the "
        "fresh harness over on the previous one's evidence and rotate forever"
    )


def test_beginning_a_session_resets_the_run_but_keeps_the_last_productive_turn(
    tmp_path,
):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    record_observed_heartbeat_turn(path, True, AT_NOON)
    drive_unproductive_turns(path, CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER)
    begin_harness_productivity_record(path, "codex", AT_NOON)
    record = read_harness_productivity_record(path)
    assert record["harness"] == "codex"
    assert consecutive_unproductive_turns(record) == 0
    assert record["last_productive_turn_at"] == AT_NOON.isoformat()


def test_three_same_harness_restarts_preserve_pending_refusal_evidence(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)

    for _turn in range(CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER):
        baseline_next_delivery(path, "session-id", 10)
        begin_harness_productivity_record(path, "opencode", AT_NOON)
        judge_pending_delivery(path, "session-id", 10, AT_NOON)

    record = read_harness_productivity_record(path)
    assert harness_is_refusing_work(record, "opencode") is True


def test_a_healthy_same_harness_restart_does_not_fabricate_a_refusal(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    judge_pending_delivery(path, "session-id", 10, AT_NOON)

    assert consecutive_unproductive_turns(read_harness_productivity_record(path)) == 0


def test_a_completed_delivery_survives_a_same_harness_restart(tmp_path):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    baseline_next_delivery(path, "session-id", 10)
    begin_harness_productivity_record(path, "opencode", AT_NOON)
    judge_pending_delivery(path, "session-id", 12, AT_NOON)

    assert consecutive_unproductive_turns(read_harness_productivity_record(path)) == 0


def test_three_transcriptless_exits_after_delivery_reach_the_refusal_threshold(
    tmp_path,
):
    path = record_path(tmp_path)
    begin_harness_productivity_record(path, "opencode", AT_NOON)

    for _turn in range(CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER):
        baseline_next_delivery(path, "harness-owned-session", None)
        judge_pending_delivery_after_session_exit(
            path, "harness-owned-session", None, AT_NOON
        )

    assert harness_is_refusing_work(read_harness_productivity_record(path), "opencode")
