import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import launch_session
import session_persistence
from harness_profile_test_helpers import make_claude_profile, make_codex_profile

CLAUDE_PROFILE = make_claude_profile()
CODEX_PROFILE = make_codex_profile()


def _write_conversation(home, workspace, session_identifier):
    project = pathlib.Path(home) / ".claude" / "projects" / workspace.replace("/", "-")
    project.mkdir(parents=True, exist_ok=True)
    (project / f"{session_identifier}.jsonl").write_text("{}\n")


def test_a_session_with_no_conversation_file_is_not_resumable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))

    assert (
        session_persistence.session_conversation_exists(
            CLAUDE_PROFILE, "abc", "/w/jenny"
        )
        is False
    )


def test_a_session_with_a_conversation_file_is_resumable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _write_conversation(tmp_path, "/w/jenny", "abc")

    assert (
        session_persistence.session_conversation_exists(
            CLAUDE_PROFILE, "abc", "/w/jenny"
        )
        is True
    )


def test_an_absent_identifier_is_never_resumable():
    assert (
        session_persistence.session_conversation_exists(
            CLAUDE_PROFILE, None, "/w/jenny"
        )
        is False
    )
    assert (
        session_persistence.session_conversation_exists(CLAUDE_PROFILE, "", "/w/jenny")
        is False
    )


def test_a_harness_owning_its_own_sessions_trusts_a_recorded_identifier(tmp_path):
    assert (
        session_persistence.session_conversation_exists(
            CODEX_PROFILE, "harness-owned-session", str(tmp_path)
        )
        is True
    ), (
        "codex keeps its sessions where clawde cannot probe them, so a recorded "
        "session must be trusted as resumable rather than probed against a claude "
        "transcript path that will never exist"
    )


def test_launch_starts_fresh_when_the_pinned_conversation_never_persisted(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        launch_session,
        "session_conversation_exists",
        lambda _profile, _identifier, _workspace_directory=None: False,
    )
    runtime_root = tmp_path / "clawde"
    (runtime_root / "session-ids").mkdir(parents=True)
    (runtime_root / "session-ids" / "jenny.json").write_text(
        '{"session_identifier": "phantom", "started_on_date": "2026-07-19"}'
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(runtime_root), "jenny", False, CLAUDE_PROFILE
    )

    assert decision.resume_previous_session is False
    assert decision.session_argv.startswith("--session-id ")
    assert "phantom" not in decision.session_argv


def test_launch_resumes_when_the_pinned_conversation_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(
        launch_session,
        "session_conversation_exists",
        lambda _profile, _identifier, _workspace_directory=None: True,
    )
    runtime_root = tmp_path / "clawde"
    (runtime_root / "session-ids").mkdir(parents=True)
    (runtime_root / "session-ids" / "jenny.json").write_text(
        '{"session_identifier": "real", "started_on_date": "2026-07-19"}'
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(runtime_root), "jenny", False, CLAUDE_PROFILE
    )

    assert decision.resume_previous_session is True
    assert decision.session_argv == "--resume real"


def test_a_pinned_conversation_is_probed_under_the_agent_workspace_not_the_wrapper_cwd(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    _write_conversation(tmp_path, "/w/jenny", "real")
    runtime_root = tmp_path / "clawde"
    (runtime_root / "session-ids").mkdir(parents=True)
    (runtime_root / "session-ids" / "jenny.json").write_text(
        '{"session_identifier": "real", "started_on_date": "2026-07-19"}'
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(runtime_root), "jenny", False, CLAUDE_PROFILE, "/w/jenny"
    )

    assert decision.resume_previous_session is True, (
        "a wrapper whose process directory is not the agent workspace must still "
        "find the pinned conversation, or every restart comes back with a zeroed "
        "session and the remembered history is filtered away with it"
    )
    assert decision.session_argv == "--resume real"


def test_remembered_history_survives_a_wrapper_running_outside_the_agent_workspace(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    _write_conversation(tmp_path, "/w/jenny", "older")
    runtime_root = tmp_path / "clawde"
    (runtime_root / "session-ids").mkdir(parents=True)
    (runtime_root / "session-ids" / "jenny.json").write_text(
        '{"session_identifier": "phantom", "started_on_date": "2026-07-19", '
        '"previous_session_identifiers": ["older"]}'
    )

    decision = launch_session.decide_and_persist_launch_session(
        str(runtime_root), "jenny", False, CLAUDE_PROFILE, "/w/jenny"
    )

    assert decision.resume_previous_session is True
    assert decision.session_argv == "--resume older"
