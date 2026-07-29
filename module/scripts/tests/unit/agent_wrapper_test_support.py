import importlib.util
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)

IDLE_REPL_PANE = "● Heartbeat scheduled, nothing pending - standing by.\n❯\n"
AUTH_FAILURE_MODAL_PANE = (
    "Please run /login · API Error: 401 Invalid authentication credentials\n"
)
USAGE_LIMIT_MODAL_PANE = (
    "What do you want to do?\n"
    " ❯ Adjust monthly spend limit\n"
    "   Wait for limit to reset\n"
)
AGENT_DISCUSSING_AUTH_ERROR_THEN_IDLE_PANE = (
    "I see the steward pane shows API Error: 401 / Please run /login - that is the\n"
    "auth-stuck state we are fixing.\n❯\n"
)


def load_agent_wrapper_module(module_name: str):
    if str(AGENT_WRAPPER_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))
    module_path = AGENT_WRAPPER_DIRECTORY / f"{module_name}.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module
