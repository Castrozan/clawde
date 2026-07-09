import importlib.util
import pathlib
import sys

SERVICE_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service"
)


def _ensure_service_directory_on_path():
    if str(SERVICE_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(SERVICE_DIRECTORY))


def load_service_module():
    _ensure_service_directory_on_path()
    module_path = SERVICE_DIRECTORY / "clawde-service.py"
    module_spec = importlib.util.spec_from_file_location("clawde_service", module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["clawde_service"] = module
    module_spec.loader.exec_module(module)
    return module


def make_tmux_supervisor_backend(fake_run_tmux_command):
    _ensure_service_directory_on_path()
    import supervisor_backend_tmux

    backend = supervisor_backend_tmux.TmuxSupervisorBackend()
    backend.run_tmux_command = fake_run_tmux_command
    return backend


class FakeCompletedProcess:
    def __init__(self, returncode, stdout=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def fake_tmux_with_window_inventory(live_session_names, windows_by_session):
    def fake_run_tmux_command(*arguments):
        subcommand = arguments[0]
        if subcommand == "has-session":
            return FakeCompletedProcess(0 if arguments[2] in live_session_names else 1)
        if subcommand == "new-session":
            session_name = arguments[3]
            live_session_names.add(session_name)
            windows_by_session.setdefault(session_name, set()).add(arguments[5])
            return FakeCompletedProcess(0)
        if subcommand == "list-windows":
            return FakeCompletedProcess(
                0, stdout="\n".join(windows_by_session.get(arguments[2], set()))
            )
        if subcommand == "new-window":
            windows_by_session.setdefault(arguments[2], set()).add(arguments[4])
            return FakeCompletedProcess(0)
        return FakeCompletedProcess(0)

    return fake_run_tmux_command


def recording_fake_tmux(live_session_names, windows_by_session):
    issued_commands = []

    def fake_run_tmux_command(*arguments):
        issued_commands.append(arguments)
        subcommand = arguments[0]
        if subcommand == "has-session":
            return FakeCompletedProcess(0 if arguments[2] in live_session_names else 1)
        if subcommand == "new-session":
            session_name = arguments[3]
            live_session_names.add(session_name)
            windows_by_session.setdefault(session_name, set()).add(arguments[5])
            return FakeCompletedProcess(0)
        if subcommand == "list-windows":
            return FakeCompletedProcess(
                0, stdout="\n".join(windows_by_session.get(arguments[2], set()))
            )
        if subcommand == "new-window":
            windows_by_session.setdefault(arguments[2], set()).add(arguments[4])
            return FakeCompletedProcess(0)
        return FakeCompletedProcess(0)

    return fake_run_tmux_command, issued_commands
