import datetime
import json
import os

HARNESS_PRODUCTIVITY_SUBDIRECTORY = "harness-productivity"
CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER = 3


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
    session_started_at = (now or datetime.datetime.now()).isoformat()
    if previous_record.get("harness") == harness_name:
        previous_record["session_started_at"] = session_started_at
        write_harness_productivity_record(record_file_path, previous_record)
        return
    write_harness_productivity_record(
        record_file_path,
        {
            "harness": harness_name,
            "consecutive_unproductive_turns": 0,
            "session_started_at": session_started_at,
            "last_productive_turn_at": previous_record.get("last_productive_turn_at"),
            "delivered_turn_pending": False,
            "delivered_turn_session_identifier": None,
            "delivered_turn_transcript_work_entry_count": None,
            "delivered_turn_showed_active_work": False,
        },
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


def harness_is_refusing_work(record: dict, harness_name: str) -> bool:
    if record.get("harness") != harness_name:
        return False
    return (
        consecutive_unproductive_turns(record)
        >= CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER
    )
