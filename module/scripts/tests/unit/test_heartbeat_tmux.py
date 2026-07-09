import importlib.util
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def _load_tmux_module():
    sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / "tmux.py"
    module_spec = importlib.util.spec_from_file_location("heartbeat_tmux", module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["heartbeat_tmux"] = module
    module_spec.loader.exec_module(module)
    return module


tmux_module = _load_tmux_module()


def test_paste_buffer_name_is_unique_per_target():
    name_for_first_agent = tmux_module.build_paste_buffer_name("clawde:bronze")
    name_for_second_agent = tmux_module.build_paste_buffer_name("copper:copper")
    assert name_for_first_agent != name_for_second_agent, (
        "two agents pasting concurrently must use distinct tmux buffer names; "
        "a shared name lets one agent's delete-buffer wipe another's before it pastes"
    )


def test_paste_buffer_name_has_no_tmux_target_separator():
    buffer_name = tmux_module.build_paste_buffer_name("copper:copper")
    assert ":" not in buffer_name, (
        "the ':' that separates session from window in a tmux target must not leak "
        "into the buffer name"
    )


def test_send_single_key_to_pane_reports_tmux_success(monkeypatch):
    recorded_arguments = []

    def fake_run_tmux_command(tmux_socket, *arguments):
        recorded_arguments.append(arguments)

        class _CompletedProcess:
            returncode = 0

        return _CompletedProcess()

    monkeypatch.setattr(tmux_module, "run_tmux_command", fake_run_tmux_command)
    assert tmux_module.send_single_key_to_pane("/socket", "clawde:steward", "Enter")
    assert recorded_arguments == [("send-keys", "-t", "clawde:steward", "Enter")]


def test_backend_prepare_returns_none_when_no_tmux_socket(monkeypatch):
    monkeypatch.setattr(tmux_module, "find_tmux_socket", lambda: None)
    backend = tmux_module.TmuxHeartbeatBackend()
    assert backend.prepare_pane_handle("clawde", "bronze") is None


def test_backend_prepare_builds_session_window_target(monkeypatch):
    monkeypatch.setattr(tmux_module, "find_tmux_socket", lambda: "/socket")
    backend = tmux_module.TmuxHeartbeatBackend()
    handle = backend.prepare_pane_handle("clawde", "bronze")
    assert handle.tmux_socket == "/socket"
    assert handle.target == "clawde:bronze"
