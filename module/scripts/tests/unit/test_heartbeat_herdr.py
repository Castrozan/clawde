import importlib.util
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def _load_herdr_module():
    sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / "herdr.py"
    module_spec = importlib.util.spec_from_file_location("heartbeat_herdr", module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["heartbeat_herdr"] = module
    module_spec.loader.exec_module(module)
    return module


herdr_module = _load_herdr_module()


class _CompletedProcessStub:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


TAB_LIST_JSON = (
    '{"result":{"tabs":['
    '{"tab_id":"wP:t1","label":"1"},'
    '{"tab_id":"wP:t7","label":"bronze"}'
    "]}}"
)
PANE_LIST_JSON = (
    '{"result":{"panes":['
    '{"pane_id":"wP:p1","tab_id":"wP:t1"},'
    '{"pane_id":"wP:p7","tab_id":"wP:t7"}'
    "]}}"
)


def test_resolve_pane_id_matches_tab_label_to_pane(monkeypatch):
    def fake_run(*arguments):
        if arguments[:2] == ("tab", "list"):
            return _CompletedProcessStub(0, TAB_LIST_JSON)
        if arguments[:2] == ("pane", "list"):
            return _CompletedProcessStub(0, PANE_LIST_JSON)
        return _CompletedProcessStub(1, "")

    monkeypatch.setattr(herdr_module, "run_herdr_command", fake_run)
    assert herdr_module.resolve_pane_id_for_tab_label("bronze") == "wP:p7"


def test_resolve_pane_id_returns_none_for_unknown_label(monkeypatch):
    monkeypatch.setattr(
        herdr_module,
        "run_herdr_command",
        lambda *arguments: _CompletedProcessStub(0, TAB_LIST_JSON),
    )
    assert herdr_module.resolve_pane_id_for_tab_label("does-not-exist") is None


def test_prepare_prefers_herdr_pane_id_environment_variable(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "wP:p42")
    backend = herdr_module.HerdrHeartbeatBackend()
    handle = backend.prepare_pane_handle("clawde", "bronze")
    assert handle.pane_id == "wP:p42"


def test_prepare_falls_back_to_label_resolution_without_env(monkeypatch):
    monkeypatch.delenv("HERDR_PANE_ID", raising=False)

    def fake_run(*arguments):
        if arguments[:2] == ("tab", "list"):
            return _CompletedProcessStub(0, TAB_LIST_JSON)
        return _CompletedProcessStub(0, PANE_LIST_JSON)

    monkeypatch.setattr(herdr_module, "run_herdr_command", fake_run)
    backend = herdr_module.HerdrHeartbeatBackend()
    handle = backend.prepare_pane_handle("clawde", "bronze")
    assert handle.pane_id == "wP:p7"


def test_capture_uses_visible_source(monkeypatch):
    recorded = []

    def fake_run(*arguments):
        recorded.append(arguments)
        return _CompletedProcessStub(0, "some output\n❯\n")

    monkeypatch.setattr(herdr_module, "run_herdr_command", fake_run)
    backend = herdr_module.HerdrHeartbeatBackend()
    handle = herdr_module.HerdrPaneHandle("wP:p7")
    content = backend.capture_recent_pane(handle)
    assert content == "some output\n❯\n"
    assert recorded[0] == (
        "pane",
        "read",
        "wP:p7",
        "--source",
        "visible",
        "--lines",
        "10",
    )


def test_send_prompt_writes_text_then_enter(monkeypatch):
    recorded = []

    def fake_run(*arguments):
        recorded.append(arguments)
        return _CompletedProcessStub(0, "")

    monkeypatch.setattr(herdr_module, "run_herdr_command", fake_run)
    backend = herdr_module.HerdrHeartbeatBackend()
    handle = herdr_module.HerdrPaneHandle("wP:p7")
    assert backend.send_prompt_to_pane(handle, "wake up")
    assert recorded == [
        ("pane", "send-text", "wP:p7", "wake up"),
        ("pane", "send-keys", "wP:p7", "Enter"),
    ]
