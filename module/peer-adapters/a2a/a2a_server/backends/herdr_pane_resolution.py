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
