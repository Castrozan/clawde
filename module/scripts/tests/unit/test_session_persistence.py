import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import launch_session
import session_persistence


def _write_conversation(home, workspace, session_identifier):
    project = pathlib.Path(home) / ".claude" / "projects" / workspace.replace("/", "-")
    project.mkdir(parents=True, exist_ok=True)
    (project / f"{session_identifier}.jsonl").write_text("{}\n")


def test_a_session_with_no_conversation_file_is_not_resumable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert session_persistence.session_conversation_exists("abc", "/w/jenny") is False


def test_a_session_with_a_conversation_file_is_resumable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_conversation(tmp_path, "/w/jenny", "abc")

    assert session_persistence.session_conversation_exists("abc", "/w/jenny") is True


def test_an_absent_identifier_is_never_resumable():
    assert session_persistence.session_conversation_exists(None, "/w/jenny") is False
    assert session_persistence.session_conversation_exists("", "/w/jenny") is False


def test_launch_starts_fresh_when_the_pinned_conversation_never_persisted(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        launch_session, "session_conversation_exists", lambda _identifier: False
    )
    runtime_root = tmp_path / "clawde"
    (runtime_root / "session-ids").mkdir(parents=True)
    (runtime_root / "session-ids" / "jenny.json").write_text(
        '{"session_identifier": "phantom", "started_on_date": "2026-07-19"}'
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(runtime_root), "jenny", False
    )

    assert decision.resume_previous_session is False
    assert decision.resume_flag.startswith("--session-id ")
    assert "phantom" not in decision.resume_flag


def test_launch_resumes_when_the_pinned_conversation_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        launch_session, "session_conversation_exists", lambda _identifier: True
    )
    runtime_root = tmp_path / "clawde"
    (runtime_root / "session-ids").mkdir(parents=True)
    (runtime_root / "session-ids" / "jenny.json").write_text(
        '{"session_identifier": "real", "started_on_date": "2026-07-19"}'
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(runtime_root), "jenny", False
    )

    assert decision.resume_previous_session is True
    assert decision.resume_flag == "--resume real"
