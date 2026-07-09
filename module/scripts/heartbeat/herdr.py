import json
import os
import subprocess

from pane_content import HeartbeatMultiplexerBackend

CAPTURE_LINE_COUNT = 10
HERDR_PANE_ID_ENVIRONMENT_VARIABLE = "HERDR_PANE_ID"


def run_herdr_command(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["herdr", *arguments],
        capture_output=True,
        text=True,
    )


def parse_herdr_json(stdout: str) -> dict | None:
    try:
        return json.loads(stdout)
    except (ValueError, TypeError):
        return None


def resolve_pane_id_for_tab_label(tab_label: str) -> str | None:
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
            if tab.get("label") == tab_label
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


class HerdrPaneHandle:
    def __init__(self, pane_id: str):
        self.pane_id = pane_id


class HerdrHeartbeatBackend(HeartbeatMultiplexerBackend):
    def prepare_pane_handle(
        self, session_name: str, window_name: str
    ) -> HerdrPaneHandle | None:
        pane_id_from_environment = os.environ.get(HERDR_PANE_ID_ENVIRONMENT_VARIABLE)
        if pane_id_from_environment:
            return HerdrPaneHandle(pane_id_from_environment)
        pane_id = resolve_pane_id_for_tab_label(window_name)
        if pane_id is None:
            return None
        return HerdrPaneHandle(pane_id)

    def capture_recent_pane(self, pane_handle: HerdrPaneHandle) -> str | None:
        result = run_herdr_command(
            "pane",
            "read",
            pane_handle.pane_id,
            "--source",
            "visible",
            "--lines",
            str(CAPTURE_LINE_COUNT),
        )
        return result.stdout if result.returncode == 0 else None

    def send_single_key_to_pane(self, pane_handle: HerdrPaneHandle, key: str) -> bool:
        result = run_herdr_command("pane", "send-keys", pane_handle.pane_id, key)
        return result.returncode == 0

    def send_prompt_to_pane(self, pane_handle: HerdrPaneHandle, content: str) -> bool:
        send_text_result = run_herdr_command(
            "pane", "send-text", pane_handle.pane_id, content
        )
        if send_text_result.returncode != 0:
            return False
        enter_result = run_herdr_command(
            "pane", "send-keys", pane_handle.pane_id, "Enter"
        )
        return enter_result.returncode == 0
