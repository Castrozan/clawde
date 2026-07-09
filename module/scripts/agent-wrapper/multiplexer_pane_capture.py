import json
import os
import subprocess

MULTIPLEXER_ENVIRONMENT_VARIABLE = "CLAWDE_MULTIPLEXER"
HERDR_MULTIPLEXER_VALUE = "herdr"
HERDR_PANE_ID_ENVIRONMENT_VARIABLE = "HERDR_PANE_ID"
HERDR_CAPTURE_SOURCE = "visible"
PANE_CAPTURE_LINE_COUNT = 80


def agent_name_from_tmux_target(tmux_target: str) -> str:
    _session_name, separator, window_name = tmux_target.partition(":")
    return window_name if separator else tmux_target


def capture_tmux_pane_content(tmux_target: str) -> str | None:
    result = subprocess.run(
        [
            "tmux",
            "capture-pane",
            "-p",
            "-t",
            tmux_target,
            "-S",
            f"-{PANE_CAPTURE_LINE_COUNT}",
        ],
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def run_herdr_command(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["herdr", *arguments], capture_output=True, text=True)


def parse_herdr_json(stdout: str) -> dict | None:
    try:
        return json.loads(stdout)
    except (ValueError, TypeError):
        return None


def resolve_herdr_pane_id_for_agent(agent_name: str) -> str | None:
    tab_list_result = run_herdr_command("tab", "list")
    if tab_list_result.returncode != 0:
        return None
    tab_list = parse_herdr_json(tab_list_result.stdout)
    if tab_list is None:
        return None
    matching_tab_id = next(
        (
            tab["tab_id"]
            for tab in tab_list.get("result", {}).get("tabs", [])
            if tab.get("label") == agent_name
        ),
        None,
    )
    if matching_tab_id is None:
        return None

    pane_list_result = run_herdr_command("pane", "list")
    if pane_list_result.returncode != 0:
        return None
    pane_list = parse_herdr_json(pane_list_result.stdout)
    if pane_list is None:
        return None
    return next(
        (
            pane["pane_id"]
            for pane in pane_list.get("result", {}).get("panes", [])
            if pane.get("tab_id") == matching_tab_id
        ),
        None,
    )


def capture_herdr_pane_content(tmux_target: str) -> str | None:
    pane_id = os.environ.get(
        HERDR_PANE_ID_ENVIRONMENT_VARIABLE
    ) or resolve_herdr_pane_id_for_agent(agent_name_from_tmux_target(tmux_target))
    if not pane_id:
        return None
    result = run_herdr_command(
        "pane",
        "read",
        pane_id,
        "--source",
        HERDR_CAPTURE_SOURCE,
        "--lines",
        str(PANE_CAPTURE_LINE_COUNT),
    )
    return result.stdout if result.returncode == 0 else None


def capture_pane_content(tmux_target: str) -> str | None:
    if os.environ.get(MULTIPLEXER_ENVIRONMENT_VARIABLE) == HERDR_MULTIPLEXER_VALUE:
        return capture_herdr_pane_content(tmux_target)
    return capture_tmux_pane_content(tmux_target)
