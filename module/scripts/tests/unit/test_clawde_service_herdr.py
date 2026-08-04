import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from herdr_backend_test_support import (
    TAB_CREATE_JSON,
    TAB_LIST_WP,
    TAB_LIST_WP_ONLY_BOOTSTRAP,
    WORKSPACE_CREATE_CLAWDE,
    WORKSPACE_LIST_WITH_CLAWDE,
    WORKSPACE_LIST_WITHOUT_CLAWDE,
    backend_with_responses,
    base,
    herdr_backend,
)


def test_start_headless_herdr_server_uses_a_transient_user_service_on_linux(
    monkeypatch,
):
    issued = []

    def record_server_start(command, **keyword_arguments):
        issued.append((command, keyword_arguments))

    monkeypatch.setattr(herdr_backend.sys, "platform", "linux")
    monkeypatch.setattr(herdr_backend.subprocess, "Popen", record_server_start)

    herdr_backend.HerdrSupervisorBackend().start_headless_herdr_server()

    assert issued == [
        (
            [
                "systemd-run",
                "--user",
                "--unit",
                "clawde-herdr-server",
                "--collect",
                "--quiet",
                "herdr",
                "server",
            ],
            {
                "stdout": herdr_backend.subprocess.DEVNULL,
                "stderr": herdr_backend.subprocess.DEVNULL,
                "stdin": herdr_backend.subprocess.DEVNULL,
                "start_new_session": True,
            },
        )
    ]


def test_agent_window_exists_is_scoped_to_the_target_workspace():
    backend = backend_with_responses(
        [],
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP),
        ],
    )
    assert backend.agent_window_exists("clawde", "bronze")
    assert not backend.agent_window_exists("clawde", "does-not-exist")


def test_agent_window_absent_when_tab_lives_in_another_workspace():
    backend = backend_with_responses(
        [],
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP_ONLY_BOOTSTRAP),
        ],
    )
    assert not backend.agent_window_exists("clawde", "bronze")


def test_create_agent_window_targets_the_resolved_workspace():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "create"), TAB_CREATE_JSON),
        ],
    )
    assert backend.create_agent_window("clawde", "bronze", "exec /nix/store/x-agent")
    assert (
        "tab",
        "create",
        "--workspace",
        "wP",
        "--label",
        "bronze",
        "--no-focus",
    ) in issued
    assert (
        "pane",
        "run",
        "wZ:p9",
        "CLAWDE_MULTIPLEXER=herdr exec /nix/store/x-agent",
    ) in issued


def test_create_agent_window_creates_the_workspace_when_missing():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITHOUT_CLAWDE),
            (("workspace", "create"), WORKSPACE_CREATE_CLAWDE),
            (("tab", "create"), TAB_CREATE_JSON),
        ],
    )
    assert backend.create_agent_window("clawde", "bronze", "exec /nix/store/x-agent")
    assert (
        "workspace",
        "create",
        "--label",
        "clawde",
        "--no-focus",
    ) in issued
    assert (
        "tab",
        "create",
        "--workspace",
        "wZ",
        "--label",
        "bronze",
        "--no-focus",
    ) in issued


def test_relaunch_replaces_the_existing_tab_before_starting_the_wrapper():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP),
            (("tab", "create"), TAB_CREATE_JSON),
        ],
    )
    assert backend.relaunch_wrapper_in_window(
        "clawde", "bronze", "exec /nix/store/x-agent"
    )
    assert ("tab", "close", "wP:t7") in issued
    assert (
        "tab",
        "create",
        "--workspace",
        "wP",
        "--label",
        "bronze",
        "--no-focus",
    ) in issued
    assert (
        "pane",
        "run",
        "wZ:p9",
        "CLAWDE_MULTIPLEXER=herdr exec /nix/store/x-agent",
    ) in issued
    assert not any(command[:3] == ("pane", "run", "wP:p7") for command in issued)


def test_remove_agent_window_closes_the_agent_tab():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP),
        ],
    )

    backend.remove_agent_window("clawde", "bronze")

    assert ("tab", "close", "wP:t7") in issued


def test_remove_agent_window_is_a_noop_when_the_tab_is_absent():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP_ONLY_BOOTSTRAP),
        ],
    )

    backend.remove_agent_window("clawde", "bronze")

    assert not any(command[:2] == ("tab", "close") for command in issued)


def test_select_supervisor_backend_dispatches_on_environment(monkeypatch):
    monkeypatch.setenv(base.MULTIPLEXER_ENVIRONMENT_VARIABLE, "herdr")
    assert isinstance(
        base.select_supervisor_backend(), herdr_backend.HerdrSupervisorBackend
    )
    monkeypatch.delenv(base.MULTIPLEXER_ENVIRONMENT_VARIABLE, raising=False)
    assert not isinstance(
        base.select_supervisor_backend(), herdr_backend.HerdrSupervisorBackend
    )
