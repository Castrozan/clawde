import importlib.util
import pathlib
import sys

SERVICE_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service"
)


def _load_module(module_file_name, module_import_name):
    if str(SERVICE_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(SERVICE_DIRECTORY))
    module_path = SERVICE_DIRECTORY / module_file_name
    module_spec = importlib.util.spec_from_file_location(
        module_import_name, module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_import_name] = module
    module_spec.loader.exec_module(module)
    return module


herdr_backend = _load_module("supervisor_backend_herdr.py", "supervisor_backend_herdr")
base = _load_module("supervisor_backend_base.py", "supervisor_backend_base")


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
PANE_LIST_JSON = '{"result":{"panes":[{"pane_id":"wP:p7","tab_id":"wP:t7"}]}}'
TAB_CREATE_JSON = '{"result":{"root_pane":{"pane_id":"wP:p9","tab_id":"wP:t9"}}}'


def test_agent_window_exists_matches_tab_label():
    backend = herdr_backend.HerdrSupervisorBackend()
    backend.run_herdr_command = lambda *arguments: _CompletedProcessStub(
        0, TAB_LIST_JSON
    )
    assert backend.agent_window_exists("clawde", "bronze")
    assert not backend.agent_window_exists("clawde", "does-not-exist")


def test_create_agent_window_makes_labeled_tab_then_runs_wrapper():
    backend = herdr_backend.HerdrSupervisorBackend()
    issued = []

    def fake_run(*arguments):
        issued.append(arguments)
        if arguments[:2] == ("tab", "create"):
            return _CompletedProcessStub(0, TAB_CREATE_JSON)
        return _CompletedProcessStub(0, "")

    backend.run_herdr_command = fake_run
    assert backend.create_agent_window("clawde", "bronze", "exec /nix/store/x-agent")
    assert issued[0] == ("tab", "create", "--label", "bronze", "--no-focus")
    assert issued[1] == ("pane", "run", "wP:p9", "exec /nix/store/x-agent")


def test_relaunch_runs_wrapper_in_existing_tab_pane():
    backend = herdr_backend.HerdrSupervisorBackend()
    issued = []

    def fake_run(*arguments):
        issued.append(arguments)
        if arguments[:2] == ("tab", "list"):
            return _CompletedProcessStub(0, TAB_LIST_JSON)
        if arguments[:2] == ("pane", "list"):
            return _CompletedProcessStub(0, PANE_LIST_JSON)
        return _CompletedProcessStub(0, "")

    backend.run_herdr_command = fake_run
    assert backend.relaunch_wrapper_in_window(
        "clawde", "bronze", "exec /nix/store/x-agent"
    )
    assert ("pane", "run", "wP:p7", "exec /nix/store/x-agent") in issued


def test_ensure_host_ready_is_a_noop_when_server_already_running():
    backend = herdr_backend.HerdrSupervisorBackend()
    backend.run_herdr_command = lambda *arguments: _CompletedProcessStub(
        0, '{"result":{"sessions":[{"running":true}]}}'
    )
    assert backend.ensure_host_ready("clawde") is False


def test_select_supervisor_backend_dispatches_on_environment(monkeypatch):
    monkeypatch.setenv(base.MULTIPLEXER_ENVIRONMENT_VARIABLE, "herdr")
    assert isinstance(
        base.select_supervisor_backend(), herdr_backend.HerdrSupervisorBackend
    )
    monkeypatch.delenv(base.MULTIPLEXER_ENVIRONMENT_VARIABLE, raising=False)
    assert not isinstance(
        base.select_supervisor_backend(), herdr_backend.HerdrSupervisorBackend
    )
