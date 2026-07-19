import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from herdr_backend_test_support import (
    PANE_LIST_JSON,
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


def test_relaunch_runs_wrapper_in_existing_workspace_scoped_tab_pane():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP),
            (("pane", "list"), PANE_LIST_JSON),
        ],
    )
    assert backend.relaunch_wrapper_in_window(
        "clawde", "bronze", "exec /nix/store/x-agent"
    )
    assert (
        "pane",
        "run",
        "wP:p7",
        "CLAWDE_MULTIPLEXER=herdr exec /nix/store/x-agent",
    ) in issued


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
