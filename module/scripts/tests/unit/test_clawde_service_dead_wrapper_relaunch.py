from clawde_service_test_helpers import (
    load_service_module,
    make_tmux_supervisor_backend,
    recording_fake_tmux,
)

service_module = load_service_module()

WRAPPER_COMMAND = "exec /nix/store/deadbeef-clawde-agent-betha-pm"


def _patch_running_wrappers(monkeypatch, running_agent_names):
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "agent_names_with_running_wrapper_after_reconcile",
        lambda session_name, declared_agent_names: set(running_agent_names),
    )


def _single_agent_specification():
    return {
        "sessions": [
            {
                "name": "clawde",
                "agents": [
                    {"name": "betha-pm", "wrapper_command": WRAPPER_COMMAND},
                ],
            }
        ]
    }


def test_relaunches_wrapper_into_existing_window_whose_wrapper_died(monkeypatch):
    _patch_running_wrappers(monkeypatch, set())
    fake_run_tmux_command, issued_commands = recording_fake_tmux(
        {"clawde"}, {"clawde": {"betha-pm"}}
    )
    backend = make_tmux_supervisor_backend(fake_run_tmux_command)
    monkeypatch.setattr(service_module.time, "sleep", lambda _seconds: None)

    service_module.ensure_all_agent_windows(backend, _single_agent_specification())

    respawn_commands = [
        command for command in issued_commands if command[0] == "respawn-window"
    ]
    assert respawn_commands == [
        ("respawn-window", "-k", "-t", "clawde:betha-pm", WRAPPER_COMMAND)
    ], (
        "the supervisor must relaunch the wrapper into an agent window that already "
        "exists but has no running wrapper; tmux-resurrect restores the window as a "
        "bare login shell on boot, and the old code returned early when the window "
        "existed and left it an idle shell forever"
    )
    assert not [command for command in issued_commands if command[0] == "new-window"], (
        "an already-existing agent window must be respawned in place, never duplicated "
        "with a second window of the same name"
    )


def test_creates_window_when_the_agent_window_is_absent(monkeypatch):
    _patch_running_wrappers(monkeypatch, set())
    fake_run_tmux_command, issued_commands = recording_fake_tmux(
        {"clawde"}, {"clawde": set()}
    )
    backend = make_tmux_supervisor_backend(fake_run_tmux_command)
    monkeypatch.setattr(service_module.time, "sleep", lambda _seconds: None)

    service_module.ensure_all_agent_windows(backend, _single_agent_specification())

    assert [command for command in issued_commands if command[0] == "new-window"] == [
        ("new-window", "-t", "clawde", "-n", "betha-pm", WRAPPER_COMMAND)
    ], "when the agent window does not exist the supervisor must still create it"
    assert not [
        command for command in issued_commands if command[0] == "respawn-window"
    ], "an absent window is created, not respawned"


def test_does_not_touch_a_window_whose_wrapper_is_already_running(monkeypatch):
    _patch_running_wrappers(monkeypatch, {"betha-pm"})
    fake_run_tmux_command, issued_commands = recording_fake_tmux(
        {"clawde"}, {"clawde": {"betha-pm"}}
    )
    backend = make_tmux_supervisor_backend(fake_run_tmux_command)
    monkeypatch.setattr(service_module.time, "sleep", lambda _seconds: None)

    service_module.ensure_all_agent_windows(backend, _single_agent_specification())

    assert not [
        command
        for command in issued_commands
        if command[0] in ("respawn-window", "new-window")
    ], (
        "a window whose wrapper is already running must never be respawned or "
        "recreated, or a live agent would be killed every poll"
    )


def test_relaunch_is_staggered_like_a_fresh_window(monkeypatch):
    _patch_running_wrappers(monkeypatch, set())
    fake_run_tmux_command, _issued_commands = recording_fake_tmux(
        {"clawde"}, {"clawde": {"betha-pm"}}
    )
    backend = make_tmux_supervisor_backend(fake_run_tmux_command)
    stagger_sleeps = []
    monkeypatch.setattr(
        service_module.time, "sleep", lambda seconds: stagger_sleeps.append(seconds)
    )

    service_module.ensure_all_agent_windows(backend, _single_agent_specification())

    assert stagger_sleeps == [service_module.AGENT_STARTUP_STAGGER_SECONDS], (
        "a respawned wrapper launches the same shared Discord plugin server as a fresh "
        "window and must be staggered just the same"
    )
