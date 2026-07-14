import importlib.util
import pathlib
import sys

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


multiplexer_pane_capture = _load_agent_wrapper_module("multiplexer_pane_capture")


class _CompletedProcessStub:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def test_agent_name_parsed_from_tmux_target():
    parse = multiplexer_pane_capture.agent_name_from_tmux_target
    assert parse("clawde:steward") == "steward"
    assert parse("no-separator") == "no-separator"


def test_tmux_backend_selected_when_multiplexer_unset(monkeypatch):
    monkeypatch.delenv("CLAWDE_MULTIPLEXER", raising=False)
    issued = {}

    def fake_run(argv, **_kwargs):
        issued["argv"] = argv
        return _CompletedProcessStub(0, "tmux-pane-content")

    monkeypatch.setattr(multiplexer_pane_capture.subprocess, "run", fake_run)
    assert (
        multiplexer_pane_capture.capture_pane_content("clawde:steward")
        == "tmux-pane-content"
    )
    assert issued["argv"][0] == "tmux"
    assert "-t" in issued["argv"] and "clawde:steward" in issued["argv"]


def test_tmux_capture_returns_none_on_nonzero(monkeypatch):
    monkeypatch.delenv("CLAWDE_MULTIPLEXER", raising=False)
    monkeypatch.setattr(
        multiplexer_pane_capture.subprocess,
        "run",
        lambda *_a, **_k: _CompletedProcessStub(1, ""),
    )
    assert multiplexer_pane_capture.capture_pane_content("clawde:steward") is None


def test_herdr_backend_reads_pane_from_env_id(monkeypatch):
    monkeypatch.setenv("CLAWDE_MULTIPLEXER", "herdr")
    monkeypatch.setenv("HERDR_PANE_ID", "wP:pE")
    issued = {}

    def fake_run(argv, **_kwargs):
        issued["argv"] = argv
        return _CompletedProcessStub(0, "some output\n❯\n")

    monkeypatch.setattr(multiplexer_pane_capture.subprocess, "run", fake_run)
    assert (
        multiplexer_pane_capture.capture_pane_content("clawde:steward")
        == "some output\n❯\n"
    )
    assert issued["argv"][:4] == ["herdr", "pane", "read", "wP:pE"]


def test_herdr_backend_resolves_pane_from_tab_label_without_env_id(monkeypatch):
    monkeypatch.setenv("CLAWDE_MULTIPLEXER", "herdr")
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    tab_list_json = '{"result":{"tabs":[{"tab_id":"wP:tE","label":"steward"}]}}'
    pane_list_json = '{"result":{"panes":[{"pane_id":"wP:pE","tab_id":"wP:tE"}]}}'
    read_pane_ids = []

    def fake_run(argv, **_kwargs):
        if argv[1:3] == ["tab", "list"]:
            return _CompletedProcessStub(0, tab_list_json)
        if argv[1:3] == ["pane", "list"]:
            return _CompletedProcessStub(0, pane_list_json)
        if argv[1:3] == ["pane", "read"]:
            read_pane_ids.append(argv[3])
            return _CompletedProcessStub(0, "resolved-pane-content")
        return _CompletedProcessStub(1, "")

    monkeypatch.setattr(multiplexer_pane_capture.subprocess, "run", fake_run)
    assert (
        multiplexer_pane_capture.capture_pane_content("clawde:steward")
        == "resolved-pane-content"
    )
    assert read_pane_ids == ["wP:pE"]


def test_herdr_backend_returns_none_when_agent_tab_absent(monkeypatch):
    monkeypatch.setenv("CLAWDE_MULTIPLEXER", "herdr")
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)

    def fake_run(argv, **_kwargs):
        if argv[1:3] == ["tab", "list"]:
            return _CompletedProcessStub(0, '{"result":{"tabs":[]}}')
        return _CompletedProcessStub(1, "")

    monkeypatch.setattr(multiplexer_pane_capture.subprocess, "run", fake_run)
    assert multiplexer_pane_capture.capture_pane_content("clawde:steward") is None


def test_send_enter_uses_tmux_send_keys_when_multiplexer_unset(monkeypatch):
    monkeypatch.delenv("CLAWDE_MULTIPLEXER", raising=False)
    issued = {}

    def fake_run(argv, **_kwargs):
        issued["argv"] = argv
        return _CompletedProcessStub(0, "")

    monkeypatch.setattr(multiplexer_pane_capture.subprocess, "run", fake_run)
    assert multiplexer_pane_capture.send_enter_key_to_pane("clawde:steward") is True
    assert issued["argv"] == ["tmux", "send-keys", "-t", "clawde:steward", "Enter"]


def test_send_enter_uses_herdr_send_keys_with_env_pane_id(monkeypatch):
    monkeypatch.setenv("CLAWDE_MULTIPLEXER", "herdr")
    monkeypatch.setenv("HERDR_PANE_ID", "wP:pE")
    issued = {}

    def fake_run(argv, **_kwargs):
        issued["argv"] = argv
        return _CompletedProcessStub(0, "")

    monkeypatch.setattr(multiplexer_pane_capture.subprocess, "run", fake_run)
    assert multiplexer_pane_capture.send_enter_key_to_pane("clawde:steward") is True
    assert issued["argv"] == ["herdr", "pane", "send-keys", "wP:pE", "Enter"]


def test_send_enter_returns_false_when_herdr_pane_cannot_be_resolved(monkeypatch):
    monkeypatch.setenv("CLAWDE_MULTIPLEXER", "herdr")
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)
    monkeypatch.setattr(
        multiplexer_pane_capture.subprocess,
        "run",
        lambda *_a, **_k: _CompletedProcessStub(0, '{"result":{"tabs":[]}}'),
    )
    assert multiplexer_pane_capture.send_enter_key_to_pane("clawde:steward") is False
