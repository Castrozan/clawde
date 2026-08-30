import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from herdr_backend_test_support import (
    CompletedProcessStub,
    TAB_CREATE_JSON,
    TAB_LIST_WP,
    TAB_LIST_WP_ONLY_BOOTSTRAP,
    WORKSPACE_CREATE_CLAWDE,
    WORKSPACE_LIST_WITH_CLAWDE,
    WORKSPACE_LIST_WITHOUT_CLAWDE,
    backend_with_responses,
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


def test_relaunch_starts_the_replacement_tab_before_discarding_the_stale_one():
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
    creation = (
        "tab",
        "create",
        "--workspace",
        "wP",
        "--label",
        "bronze",
        "--no-focus",
    )
    assert issued.index(creation) < issued.index(("tab", "close", "wP:t7"))
    assert (
        "pane",
        "run",
        "wZ:p9",
        "CLAWDE_MULTIPLEXER=herdr exec /nix/store/x-agent",
    ) in issued
    assert not any(command[:3] == ("pane", "run", "wP:p7") for command in issued)


def test_relaunch_revives_an_agent_whose_tab_is_the_last_one_in_its_workspace():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP),
            (("tab", "create"), TAB_CREATE_JSON),
        ],
    )
    creating_run = backend.run_herdr_command

    def run_refusing_to_close_the_last_tab(*arguments):
        if arguments[:2] == ("tab", "close"):
            issued.append(arguments)
            refusal = CompletedProcessStub(1, "")
            refusal.stderr = (
                '{"error":{"code":"tab_close_failed",'
                '"message":"cannot close the last tab in a workspace"}}'
            )
            return refusal
        return creating_run(*arguments)

    backend.run_herdr_command = run_refusing_to_close_the_last_tab

    assert backend.relaunch_wrapper_in_window(
        "clawde", "bronze", "exec /nix/store/x-agent"
    )
    assert (
        "pane",
        "run",
        "wZ:p9",
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
