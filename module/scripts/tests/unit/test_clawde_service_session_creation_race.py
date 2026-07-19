from clawde_service_test_helpers import (
    FakeCompletedProcess,
    load_service_module,
    make_tmux_supervisor_backend,
)

service_module = load_service_module()


def _patch_no_running_wrappers(monkeypatch):
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_running_wrapper_after_reconcile",
        lambda session_name, declared_agent_names: set(),
    )


def test_session_creation_tolerates_a_concurrent_creator_without_crashing(monkeypatch):
    _patch_no_running_wrappers(monkeypatch)
    session_state = {"exists": False}
    issued_commands = []

    def fake_run_tmux_command(*arguments):
        issued_commands.append(arguments)
        subcommand = arguments[0]
        if subcommand == "has-session":
            return FakeCompletedProcess(0 if session_state["exists"] else 1)
        if subcommand == "new-session":
            session_state["exists"] = True
            return FakeCompletedProcess(1)
        if subcommand == "list-windows":
            return FakeCompletedProcess(0, stdout="")
        return FakeCompletedProcess(0)

    backend = make_tmux_supervisor_backend(fake_run_tmux_command)
    monkeypatch.setattr(service_module.time, "sleep", lambda _seconds: None)

    specification = {
        "sessions": [
            {
                "name": "clawde",
                "agents": [{"name": "betha-pm", "wrapper_command": "true"}],
            }
        ]
    }

    service_module.ensure_all_agent_windows(
        backend,
        specification,
        service_module.launch_gate_decision.LaunchGateScheduler(),
    )

    assert [command for command in issued_commands if command[0] == "new-window"] == [
        ("new-window", "-t", "clawde", "-n", "betha-pm", "true")
    ], (
        "when tmux-resurrect wins the race and creates the declared session a tick "
        "before the supervisor's new-session, that benign duplicate-session failure "
        "must not crash the supervisor; it must proceed to ensure the agent window in "
        "the now-existing session"
    )
