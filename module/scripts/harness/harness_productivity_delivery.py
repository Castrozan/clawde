import datetime

from harness_productivity_record import (
    read_harness_productivity_record,
    record_observed_heartbeat_turn,
    write_harness_productivity_record,
)

TRANSCRIPT_WORK_ENTRIES_A_PRODUCTIVE_TURN_ADDS = 1


def delivered_turn_produced_work(
    record: dict,
    session_identifier: str | None,
    transcript_work_entry_count: int | None,
) -> bool:
    if record.get("delivered_turn_showed_active_work"):
        return True
    if transcript_work_entry_count is None:
        return True
    if record.get("delivered_turn_session_identifier") != session_identifier:
        return True
    entry_count_before_delivery = record.get(
        "delivered_turn_transcript_work_entry_count"
    )
    if not isinstance(entry_count_before_delivery, int):
        return True
    return (
        transcript_work_entry_count - entry_count_before_delivery
        >= TRANSCRIPT_WORK_ENTRIES_A_PRODUCTIVE_TURN_ADDS
    )


def baseline_next_delivery(
    record_file_path: str,
    session_identifier: str | None,
    transcript_work_entry_count: int | None,
) -> dict:
    record = read_harness_productivity_record(record_file_path)
    record["delivered_turn_pending"] = True
    record["delivered_turn_session_identifier"] = session_identifier
    record["delivered_turn_transcript_work_entry_count"] = transcript_work_entry_count
    record["delivered_turn_showed_active_work"] = False
    write_harness_productivity_record(record_file_path, record)
    return record


def record_pending_delivery_judgment(
    record_file_path: str,
    turn_was_productive: bool,
    now: datetime.datetime | None = None,
) -> dict:
    judged_record = record_observed_heartbeat_turn(
        record_file_path,
        turn_was_productive,
        now,
    )
    judged_record["delivered_turn_pending"] = False
    judged_record["delivered_turn_session_identifier"] = None
    judged_record["delivered_turn_transcript_work_entry_count"] = None
    judged_record["delivered_turn_showed_active_work"] = False
    write_harness_productivity_record(record_file_path, judged_record)
    return judged_record


def judge_pending_delivery(
    record_file_path: str,
    session_identifier: str | None,
    transcript_work_entry_count: int | None,
    now: datetime.datetime | None = None,
) -> dict:
    record = read_harness_productivity_record(record_file_path)
    if record.get("delivered_turn_pending") is not True:
        return record
    return record_pending_delivery_judgment(
        record_file_path,
        delivered_turn_produced_work(
            record,
            session_identifier,
            transcript_work_entry_count,
        ),
        now,
    )


def judge_pending_delivery_after_session_exit(
    record_file_path: str,
    session_identifier: str | None,
    transcript_work_entry_count: int | None,
    now: datetime.datetime | None = None,
) -> dict:
    record = read_harness_productivity_record(record_file_path)
    if record.get("delivered_turn_pending") is not True:
        return record
    turn_was_productive = bool(record.get("delivered_turn_showed_active_work")) or (
        transcript_work_entry_count is not None
        and delivered_turn_produced_work(
            record,
            session_identifier,
            transcript_work_entry_count,
        )
    )
    return record_pending_delivery_judgment(record_file_path, turn_was_productive, now)


def judge_previous_turn_and_baseline_the_next(
    record_file_path: str,
    session_identifier: str | None,
    transcript_work_entry_count: int | None,
    now: datetime.datetime | None = None,
) -> dict:
    judge_pending_delivery(
        record_file_path, session_identifier, transcript_work_entry_count, now
    )
    return baseline_next_delivery(
        record_file_path, session_identifier, transcript_work_entry_count
    )


def record_that_the_delivered_turn_showed_active_work(record_file_path: str) -> dict:
    record = read_harness_productivity_record(record_file_path)
    record["delivered_turn_showed_active_work"] = True
    write_harness_productivity_record(record_file_path, record)
    return record
