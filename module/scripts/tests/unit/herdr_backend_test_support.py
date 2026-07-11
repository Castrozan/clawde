import importlib.util
import pathlib
import sys

SERVICE_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service"
)


def load_service_module(module_file_name, module_import_name):
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


herdr_backend = load_service_module(
    "supervisor_backend_herdr.py", "supervisor_backend_herdr"
)
base = load_service_module("supervisor_backend_base.py", "supervisor_backend_base")


class CompletedProcessStub:
    def __init__(self, returncode, stdout):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


WORKSPACE_LIST_WITH_CLAWDE = (
    '{"result":{"workspaces":['
    '{"workspace_id":"wA","label":"other"},'
    '{"workspace_id":"wP","label":"clawde"}'
    "]}}"
)
WORKSPACE_LIST_WITHOUT_CLAWDE = (
    '{"result":{"workspaces":[{"workspace_id":"wA","label":"other"}]}}'
)
WORKSPACE_CREATE_CLAWDE = (
    '{"result":{"workspace":{"workspace_id":"wZ","label":"clawde"}}}'
)
TAB_LIST_WP = (
    '{"result":{"tabs":['
    '{"tab_id":"wP:t1","label":"1"},'
    '{"tab_id":"wP:t7","label":"bronze"}'
    "]}}"
)
TAB_LIST_WP_ONLY_BOOTSTRAP = '{"result":{"tabs":[{"tab_id":"wP:t1","label":"1"}]}}'
PANE_LIST_JSON = '{"result":{"panes":[{"pane_id":"wP:p7","tab_id":"wP:t7"}]}}'
TAB_CREATE_JSON = '{"result":{"root_pane":{"pane_id":"wZ:p9","tab_id":"wZ:t9"}}}'
SERVER_RUNNING_JSON = '{"sessions":[{"default":true,"name":"default","running":true}]}'


def dispatching_fake_run(issued, responses):
    def fake_run(*arguments):
        issued.append(arguments)
        for prefix, stdout in responses:
            if arguments[: len(prefix)] == prefix:
                return CompletedProcessStub(0, stdout)
        return CompletedProcessStub(0, "")

    return fake_run


def backend_with_responses(issued, responses):
    backend = herdr_backend.HerdrSupervisorBackend()
    backend.run_herdr_command = dispatching_fake_run(issued, responses)
    return backend
