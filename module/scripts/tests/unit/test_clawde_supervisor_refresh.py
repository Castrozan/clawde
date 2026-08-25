import importlib.util
import pathlib

CLAWDE_SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent.parent


def _load_supervisor_refresh_module():
    module_spec = importlib.util.spec_from_file_location(
        "clawde_supervisor_refresh",
        CLAWDE_SCRIPTS_DIRECTORY / "clawde-supervisor-refresh.py",
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


supervisor_refresh = _load_supervisor_refresh_module()

DEPLOYED_COMMAND = "/nix/store/new-python3 /nix/store/new-clawde-service.py --specification-file /nix/store/new-spec.json"
SUPERSEDED_COMMAND = "/nix/store/old-python3 /nix/store/old-clawde-service.py --specification-file /nix/store/old-spec.json"


def stub_live_supervisors(monkeypatch, command_lines):
    process_ids = list(range(100, 100 + len(command_lines)))
    monkeypatch.setattr(
        supervisor_refresh, "find_supervisor_process_ids", lambda: process_ids
    )
    monkeypatch.setattr(
        supervisor_refresh,
        "read_full_command_line",
        lambda process_id: command_lines[process_ids.index(process_id)],
    )


def test_a_supervisor_running_superseded_code_is_restarted(monkeypatch, tmp_path):
    stub_live_supervisors(monkeypatch, [SUPERSEDED_COMMAND])

    assert supervisor_refresh.supervisor_runs_superseded_code(DEPLOYED_COMMAND)


def test_a_supervisor_already_on_this_generation_is_left_alone(monkeypatch):
    stub_live_supervisors(monkeypatch, [DEPLOYED_COMMAND])

    assert not supervisor_refresh.supervisor_runs_superseded_code(DEPLOYED_COMMAND)


def test_no_running_supervisor_needs_no_restart(monkeypatch):
    stub_live_supervisors(monkeypatch, [])

    assert not supervisor_refresh.supervisor_runs_superseded_code(DEPLOYED_COMMAND)


def test_an_unreadable_command_line_never_triggers_a_restart(monkeypatch):
    stub_live_supervisors(monkeypatch, [""])

    assert not supervisor_refresh.supervisor_runs_superseded_code(DEPLOYED_COMMAND)


def test_the_refresh_never_matches_its_own_process(monkeypatch):
    monkeypatch.setattr(
        supervisor_refresh,
        "inspect_processes",
        lambda _command: f"{__import__('os').getpid()}\n",
    )

    assert supervisor_refresh.find_supervisor_process_ids() == []


def test_a_missing_process_tool_never_breaks_the_activation(monkeypatch):
    def raise_missing_tool(*_args, **_keywords):
        raise FileNotFoundError(2, "No such file or directory", "pgrep")

    monkeypatch.setattr(supervisor_refresh.subprocess, "run", raise_missing_tool)

    assert supervisor_refresh.find_supervisor_process_ids() == []
    assert supervisor_refresh.read_full_command_line(4321) == ""
    assert not supervisor_refresh.supervisor_runs_superseded_code(DEPLOYED_COMMAND)


def test_the_deployed_command_is_read_from_its_file(tmp_path):
    command_file = tmp_path / "clawde-service-deployed-command"
    command_file.write_text(DEPLOYED_COMMAND + "\n")

    assert (
        supervisor_refresh.read_deployed_command(str(command_file)) == DEPLOYED_COMMAND
    )


def test_main_restarts_only_when_the_running_code_is_superseded(monkeypatch, tmp_path):
    command_file = tmp_path / "clawde-service-deployed-command"
    command_file.write_text(DEPLOYED_COMMAND)
    restart_commands = []
    monkeypatch.setattr(
        supervisor_refresh,
        "parse_arguments",
        lambda: type(
            "Arguments",
            (),
            {
                "deployed_command_file": str(command_file),
                "restart_command": "restart-me",
            },
        ),
    )
    monkeypatch.setattr(
        supervisor_refresh,
        "restart_the_supervisor",
        lambda command: restart_commands.append(command) or 0,
    )

    stub_live_supervisors(monkeypatch, [DEPLOYED_COMMAND])
    assert supervisor_refresh.main() == 0
    assert restart_commands == []

    stub_live_supervisors(monkeypatch, [SUPERSEDED_COMMAND])
    assert supervisor_refresh.main() == 0
    assert restart_commands == ["restart-me"]
