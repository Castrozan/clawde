import json
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import session_store

AGENT_NAME = "on-demand-agent"


def write_record(runtime_root, session_identifier, started_on_date, previous=None):
    record_path = pathlib.Path(
        session_store.build_session_record_file_path(str(runtime_root), AGENT_NAME)
    )
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(
        json.dumps(
            {
                "session_identifier": session_identifier,
                "started_on_date": started_on_date,
                "previous_session_identifiers": previous or [],
            }
        )
    )
    return record_path


def test_forgetting_the_pinned_session_promotes_the_next_and_keeps_the_rest(tmp_path):
    record_path = write_record(tmp_path / "clawde", "s1", "2026-07-19", ["s2", "s3"])

    session_store.forget_session_identifier_from_record(str(record_path), "s1")

    record = json.loads(record_path.read_text())
    assert record["session_identifier"] == "s2"
    assert record["previous_session_identifiers"] == ["s3"]


def test_forgetting_the_only_session_clears_the_record(tmp_path):
    record_path = write_record(tmp_path / "clawde", "s1", "2026-07-19")

    session_store.forget_session_identifier_from_record(str(record_path), "s1")

    assert not record_path.exists()


def test_forgetting_a_remembered_id_leaves_the_pinned_session_intact(tmp_path):
    record_path = write_record(tmp_path / "clawde", "s1", "2026-07-19", ["s2", "s3"])

    session_store.forget_session_identifier_from_record(str(record_path), "s2")

    record = json.loads(record_path.read_text())
    assert record["session_identifier"] == "s1"
    assert record["previous_session_identifiers"] == ["s3"]
