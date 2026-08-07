import datetime
import json
import os

HARNESS_PRODUCTIVITY_SUBDIRECTORY = "harness-productivity"
CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER = 3
TRANSCRIPT_ENTRIES_A_PRODUCTIVE_TURN_ADDS = 2


def harness_productivity_record_path(
    runtime_root_directory: str, agent_name: str
) -> str:
    return os.path.join(
        runtime_root_directory,
        HARNESS_PRODUCTIVITY_SUBDIRECTORY,
        f"{agent_name}.json",
    )


def read_harness_productivity_record(record_file_path: str) -> dict:
    try:
        with open(record_file_path) as record_file:
            record = json.load(record_file)
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def write_harness_productivity_record(record_file_path: str, record: dict) -> None:
    os.makedirs(os.path.dirname(record_file_path), exist_ok=True)
    with open(record_file_path, "w") as record_file:
        json.dump(record, record_file)


def consecutive_unproductive_turns(record: dict) -> int:
    counted_turns = record.get("consecutive_unproductive_turns")
    return counted_turns if isinstance(counted_turns, int) else 0


def begin_harness_productivity_record(
    record_file_path: str,
    harness_name: str,
    now: datetime.datetime | None = None,
) -> None:
    previous_record = read_harness_productivity_record(record_file_path)
    write_harness_productivity_record(
        record_file_path,
        {
            "harness": harness_name,
            "consecutive_unproductive_turns": 0,
            "session_started_at": (now or datetime.datetime.now()).isoformat(),
            "last_productive_turn_at": previous_record.get("last_productive_turn_at"),
            "delivered_turn_session_identifier": None,
            "delivered_turn_transcript_entry_count": None,
            "delivered_turn_showed_active_work": False,
        },
    )


def delivered_turn_produced_work(
    record: dict,
    session_identifier: str | None,
    transcript_entry_count: int | None,
) -> bool:
    if record.get("delivered_turn_showed_active_work"):
        return True
    if transcript_entry_count is None:
        return True
    if record.get("delivered_turn_session_identifier") != session_identifier:
        return True
    entry_count_before_delivery = record.get("delivered_turn_transcript_entry_count")
    if not isinstance(entry_count_before_delivery, int):
        return True
    return (
        transcript_entry_count - entry_count_before_delivery
        >= TRANSCRIPT_ENTRIES_A_PRODUCTIVE_TURN_ADDS
    )


def record_observed_heartbeat_turn(
    record_file_path: str,
    turn_was_productive: bool,
    now: datetime.datetime | None = None,
) -> dict:
    observed_at = (now or datetime.datetime.now()).isoformat()
    record = read_harness_productivity_record(record_file_path)
    record["consecutive_unproductive_turns"] = (
        0 if turn_was_productive else consecutive_unproductive_turns(record) + 1
    )
    record["last_turn_observed_at"] = observed_at
    if turn_was_productive:
        record["last_productive_turn_at"] = observed_at
    write_harness_productivity_record(record_file_path, record)
    return record


def judge_previous_turn_and_baseline_the_next(
    record_file_path: str,
    session_identifier: str | None,
    transcript_entry_count: int | None,
    now: datetime.datetime | None = None,
) -> dict:
    judged_record = record_observed_heartbeat_turn(
        record_file_path,
        delivered_turn_produced_work(
            read_harness_productivity_record(record_file_path),
            session_identifier,
            transcript_entry_count,
        ),
        now,
    )
    judged_record["delivered_turn_session_identifier"] = session_identifier
    judged_record["delivered_turn_transcript_entry_count"] = transcript_entry_count
    judged_record["delivered_turn_showed_active_work"] = False
    write_harness_productivity_record(record_file_path, judged_record)
    return judged_record


def record_that_the_delivered_turn_showed_active_work(record_file_path: str) -> dict:
    record = read_harness_productivity_record(record_file_path)
    record["delivered_turn_showed_active_work"] = True
    write_harness_productivity_record(record_file_path, record)
    return record


def harness_is_refusing_work(record: dict, harness_name: str) -> bool:
    if record.get("harness") != harness_name:
        return False
    return (
        consecutive_unproductive_turns(record)
        >= CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER
    )
