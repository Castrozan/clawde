import importlib.util
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)


def _load_session_store_module():
    if str(AGENT_WRAPPER_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))
    module_path = AGENT_WRAPPER_DIRECTORY / "session_store.py"
    module_spec = importlib.util.spec_from_file_location("session_store", module_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


session_store = _load_session_store_module()


def test_build_path_nests_under_the_session_ids_subdirectory(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "ai-first")
    assert path == str(tmp_path / "session-ids" / "ai-first.json")


def test_reading_an_absent_record_returns_a_none_pair(tmp_path):
    absent = session_store.build_session_record_file_path(str(tmp_path), "steward")
    assert session_store.read_persisted_session_record(absent) == (None, None)


def test_write_then_read_round_trips_the_id_and_start_date(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "steward")
    session_store.write_persisted_session_record(path, "pinned-id", "2026-07-14")
    assert session_store.read_persisted_session_record(path) == (
        "pinned-id",
        "2026-07-14",
    )


def test_reading_a_record_with_an_empty_id_returns_a_none_pair(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "steward")
    session_store.write_persisted_session_record(path, "", "2026-07-14")
    assert session_store.read_persisted_session_record(path) == (None, None)


def test_reading_a_corrupt_record_returns_a_none_pair(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "steward")
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(path).write_text("not json {{{")
    assert session_store.read_persisted_session_record(path) == (None, None)


def test_clear_removes_the_record_so_the_next_launch_starts_fresh(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "steward")
    session_store.write_persisted_session_record(path, "dead-id", "2026-07-14")
    session_store.clear_persisted_session_record(path)
    assert session_store.read_persisted_session_record(path) == (None, None)


def test_clearing_an_absent_record_is_a_noop(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "steward")
    session_store.clear_persisted_session_record(path)


def test_persistence_survives_a_new_reader_with_no_prior_state(tmp_path):
    path = session_store.build_session_record_file_path(str(tmp_path), "jenny")
    session_store.write_persisted_session_record(path, "survives-respawn", "2026-07-14")
    reloaded = _load_session_store_module()
    assert reloaded.read_persisted_session_record(path) == (
        "survives-respawn",
        "2026-07-14",
    )
