import importlib.util
import pathlib
import sys

import pytest
import time

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)


def _load_agent_wrapper_module(module_name: str):
    if str(AGENT_WRAPPER_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))
    module_path = AGENT_WRAPPER_DIRECTORY / f"{module_name}.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


launch_session = _load_agent_wrapper_module("launch_session")
session_store = _load_agent_wrapper_module("session_store")

TODAY = time.strftime("%Y-%m-%d")


def _seed(tmp_path, agent_name, session_identifier, started_on_date):
    path = session_store.build_session_record_file_path(str(tmp_path), agent_name)
    session_store.write_persisted_session_record(
        path, session_identifier, started_on_date
    )
    return path


def test_first_launch_with_no_record_pins_a_fresh_session_and_persists_today(tmp_path):
    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "ai-first", daily_session_rotation=False
    )
    assert decision.resume_flag.startswith("--session-id ")
    assert decision.resume_previous_session is False
    pinned = decision.resume_flag.removeprefix("--session-id ")
    assert session_store.read_persisted_session_record(
        decision.session_record_file_path
    ) == (pinned, TODAY)


def test_a_restart_with_a_persisted_id_resumes_that_exact_session(tmp_path):
    _seed(tmp_path, "ai-first", "S1", TODAY)
    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "ai-first", daily_session_rotation=False
    )
    assert decision.resume_flag == "--resume S1"
    assert decision.resume_previous_session is True


def test_a_fresh_wrapper_process_still_resumes_from_the_persisted_record(tmp_path):
    _seed(tmp_path, "jenny", "S9", TODAY)
    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "jenny", daily_session_rotation=False
    )
    assert decision.resume_flag == "--resume S9", (
        "a wrapper respawn loses in-memory state but must still resume the session "
        "id pinned on disk, instead of starting the agent empty"
    )


def test_rotation_day_launches_fresh_even_with_a_persisted_id(tmp_path):
    _seed(tmp_path, "golden", "S-OLD", "1999-01-01")
    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "golden", daily_session_rotation=True
    )
    assert decision.resume_flag.startswith("--session-id ")
    assert decision.rotating_session is True
    assert decision.resume_previous_session is False


def test_rotation_survives_a_respawn_because_the_start_date_is_on_disk(tmp_path):
    _seed(tmp_path, "golden", "S-OLD", "1999-01-01")
    first = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "golden", daily_session_rotation=True
    )
    assert first.rotating_session is True
    fresh_id = first.resume_flag.removeprefix("--session-id ")
    assert session_store.read_persisted_session_record(
        first.session_record_file_path
    ) == (fresh_id, TODAY)


def test_rotation_off_resumes_even_a_day_old_session(tmp_path):
    _seed(tmp_path, "betha-pm", "S-OLD", "1999-01-01")
    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "betha-pm", daily_session_rotation=False
    )
    assert decision.resume_flag == "--resume S-OLD"
    assert decision.rotating_session is False


def test_rotation_on_within_the_same_day_still_resumes(tmp_path):
    _seed(tmp_path, "golden", "S-TODAY", TODAY)
    decision = launch_session.decide_and_persist_launch_session(
        str(tmp_path), "golden", daily_session_rotation=True
    )
    assert decision.resume_flag == "--resume S-TODAY"
    assert decision.rotating_session is False


@pytest.fixture(autouse=True)
def a_pinned_conversation_is_assumed_to_exist(monkeypatch):
    monkeypatch.setattr(
        launch_session, "session_conversation_exists", lambda _identifier: True
    )
