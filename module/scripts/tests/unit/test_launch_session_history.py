import json
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import launch_session
import session_persistence
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


def create_conversation(home_directory, workspace_directory, session_identifier):
    project_directory = session_persistence.claude_project_directory_for_workspace(
        workspace_directory
    )
    project_directory.mkdir(parents=True, exist_ok=True)
    (project_directory / f"{session_identifier}.jsonl").write_text("{}\n")


def test_a_persisted_session_with_a_conversation_is_resumed(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    create_conversation(tmp_path, str(tmp_path), "session-one")
    write_record(tmp_path / "clawde", "session-one", "2026-07-19")

    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, False
    )

    assert decision.resume_previous_session is True
    assert decision.resume_flag == "--resume session-one"
    capsys.readouterr()


def test_a_stale_pointer_falls_back_to_a_remembered_session_with_a_conversation(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    create_conversation(tmp_path, str(tmp_path), "session-old")
    write_record(
        tmp_path / "clawde", "session-never-used", "2026-07-19", ["session-old"]
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, False
    )

    assert decision.resume_flag == "--resume session-old"


def test_a_stale_pointer_with_no_usable_history_starts_fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    write_record(tmp_path / "clawde", "session-never-used", "2026-07-19", ["also-gone"])

    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, False
    )

    assert decision.resume_previous_session is False
    assert decision.resume_flag.startswith("--session-id ")


def test_a_retired_session_with_a_conversation_is_remembered_after_rotation(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    create_conversation(tmp_path, str(tmp_path), "yesterdays-session")
    record_path = write_record(tmp_path / "clawde", "yesterdays-session", "2026-01-01")

    launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, True
    )

    assert json.loads(record_path.read_text())["previous_session_identifiers"] == [
        "yesterdays-session"
    ]


def test_a_retired_phantom_session_is_not_remembered_after_rotation(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    record_path = write_record(tmp_path / "clawde", "phantom-session", "2026-01-01")

    launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, True
    )

    assert json.loads(record_path.read_text())["previous_session_identifiers"] == []


def test_a_phantom_pointer_does_not_bury_the_good_session_in_history(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    create_conversation(tmp_path, str(tmp_path), "good-session")
    record_path = write_record(
        tmp_path / "clawde", "phantom-latest", "2026-07-19", ["good-session"]
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, False
    )

    assert decision.resume_flag == "--resume good-session"
    assert (
        "phantom-latest"
        not in json.loads(record_path.read_text())["previous_session_identifiers"]
    )


def test_daily_rotation_still_starts_fresh_despite_a_resumable_history(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    create_conversation(tmp_path, str(tmp_path), "session-old")
    write_record(tmp_path / "clawde", "session-old", "2026-01-01")

    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path / "clawde"), AGENT_NAME, True
    )

    assert decision.rotating_session is True
    assert decision.resume_previous_session is False


def test_remembering_drops_duplicates_and_the_current_session():
    remembered = session_store.remember_previous_session_identifiers(
        "session-b", ["session-a", "session-b", "session-c"], "session-a"
    )

    assert remembered == ["session-b", "session-c"]


def test_remembering_is_capped():
    previously_remembered = [f"session-{index}" for index in range(20)]

    remembered = session_store.remember_previous_session_identifiers(
        "session-retiring", previously_remembered, "session-current"
    )

    assert len(remembered) == session_store.REMEMBERED_PREVIOUS_SESSION_LIMIT
    assert remembered[0] == "session-retiring"


def test_a_record_without_a_history_key_reads_as_an_empty_history(tmp_path):
    record_path = tmp_path / "agent.json"
    record_path.write_text(json.dumps({"session_identifier": "session-one"}))

    assert session_store.read_previous_session_identifiers(str(record_path)) == []


def test_a_record_with_a_malformed_history_reads_as_an_empty_history(tmp_path):
    record_path = tmp_path / "agent.json"
    record_path.write_text(
        json.dumps(
            {"session_identifier": "one", "previous_session_identifiers": "nope"}
        )
    )

    assert session_store.read_previous_session_identifiers(str(record_path)) == []
