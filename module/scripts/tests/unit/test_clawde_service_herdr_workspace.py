import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from herdr_backend_test_support import (
    SERVER_RUNNING_JSON,
    TAB_LIST_WP,
    TAB_LIST_WP_ONLY_BOOTSTRAP,
    WORKSPACE_CREATE_CLAWDE,
    WORKSPACE_LIST_WITH_CLAWDE,
    WORKSPACE_LIST_WITHOUT_CLAWDE,
    backend_with_responses,
)


def test_find_workspace_id_for_label_resolves_by_label():
    backend = backend_with_responses(
        [], [(("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE)]
    )
    assert backend.find_workspace_id_for_label("clawde") == "wP"
    assert backend.find_workspace_id_for_label("missing") is None


def test_ensure_workspace_returns_existing_without_creating():
    issued = []
    backend = backend_with_responses(
        issued, [(("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE)]
    )
    assert backend.ensure_workspace("clawde") == "wP"
    assert not any(arguments[:2] == ("workspace", "create") for arguments in issued)


def test_ensure_workspace_creates_when_absent():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITHOUT_CLAWDE),
            (("workspace", "create"), WORKSPACE_CREATE_CLAWDE),
        ],
    )
    assert backend.ensure_workspace("clawde") == "wZ"
    assert (
        "workspace",
        "create",
        "--label",
        "clawde",
        "--no-focus",
    ) in issued


def test_ensure_host_ready_creates_the_workspace_and_reports_scaffolding():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("session", "list", "--json"), SERVER_RUNNING_JSON),
            (("workspace", "list"), WORKSPACE_LIST_WITHOUT_CLAWDE),
            (("workspace", "create"), WORKSPACE_CREATE_CLAWDE),
        ],
    )
    assert backend.ensure_host_ready("clawde") is True
    assert (
        "workspace",
        "create",
        "--label",
        "clawde",
        "--no-focus",
    ) in issued


def test_ensure_host_ready_is_a_noop_when_workspace_already_present():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("session", "list", "--json"), SERVER_RUNNING_JSON),
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
        ],
    )
    assert backend.ensure_host_ready("clawde") is False
    assert not any(arguments[:2] == ("workspace", "create") for arguments in issued)


def test_remove_bootstrap_scaffolding_closes_the_default_tab():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP),
        ],
    )
    backend.remove_bootstrap_scaffolding("clawde")
    assert ("tab", "close", "wP:t1") in issued


def test_remove_bootstrap_scaffolding_keeps_the_last_remaining_tab():
    issued = []
    backend = backend_with_responses(
        issued,
        [
            (("workspace", "list"), WORKSPACE_LIST_WITH_CLAWDE),
            (("tab", "list", "--workspace"), TAB_LIST_WP_ONLY_BOOTSTRAP),
        ],
    )
    backend.remove_bootstrap_scaffolding("clawde")
    assert not any(arguments[:2] == ("tab", "close") for arguments in issued)
