import importlib.util
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def load_heartbeat_module(module_name: str):
    if str(HEARTBEAT_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / f"{module_name}.py"
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module
