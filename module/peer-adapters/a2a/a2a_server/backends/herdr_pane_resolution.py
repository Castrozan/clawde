import json
import subprocess


def run_herdr_command(arguments: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["herdr", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def read_herdr_result(arguments: list[str]) -> dict:
    result = run_herdr_command(arguments)
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)["result"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}


def find_identifier_of_labelled_entry(
    arguments: list[str], collection_key: str, identifier_key: str, label: str
) -> str | None:
    collection = read_herdr_result(arguments).get(collection_key, [])
    return next(
        (entry[identifier_key] for entry in collection if entry.get("label") == label),
        None,
    )


def find_pane_id_hosting_the_agent_tab(
    workspace_label: str, tab_label: str
) -> str | None:
    workspace_id = find_identifier_of_labelled_entry(
        ["workspace", "list"], "workspaces", "workspace_id", workspace_label
    )
    if workspace_id is None:
        return None
    tab_id = find_identifier_of_labelled_entry(
        ["tab", "list", "--workspace", workspace_id], "tabs", "tab_id", tab_label
    )
    if tab_id is None:
        return None
    panes = read_herdr_result(["pane", "list"]).get("panes", [])
    return next(
        (pane["pane_id"] for pane in panes if pane.get("tab_id") == tab_id),
        None,
    )


def read_pane_information(pane_id: str | None) -> dict:
    if pane_id is None:
        return {}
    return read_herdr_result(["pane", "get", pane_id]).get("pane", {})


def capture_pane_text(pane_id: str, capture_line_count: int) -> str:
    result = run_herdr_command(
        [
            "pane",
            "read",
            pane_id,
            "--source",
            "recent-unwrapped",
            "--lines",
            str(capture_line_count),
        ]
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def send_text_to_pane(pane_id: str, text: str) -> None:
    run_herdr_command(["pane", "send-text", pane_id, text])


def send_key_to_pane(pane_id: str, key: str) -> None:
    run_herdr_command(["pane", "send-keys", pane_id, key])
