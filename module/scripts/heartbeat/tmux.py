import os
import subprocess
import sys
import tempfile

from pane_content import HeartbeatMultiplexerBackend


def find_tmux_socket() -> str | None:
    tmux_tmpdir = os.environ.get("TMUX_TMPDIR")
    uid = os.getuid()
    candidate_directories = ([tmux_tmpdir] if tmux_tmpdir else []) + [
        f"/run/user/{uid}/tmux-{uid}",
        f"/tmp/tmux-{uid}",
    ]
    for directory in candidate_directories:
        if os.path.exists(directory):
            socket_path = os.path.join(directory, "default")
            if os.path.exists(socket_path):
                return socket_path
    return None


def run_tmux_command(tmux_socket: str, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["tmux", "-S", tmux_socket, *arguments],
        capture_output=True,
        text=True,
    )


def send_single_key_to_pane(tmux_socket: str, target: str, key: str) -> bool:
    result = run_tmux_command(tmux_socket, "send-keys", "-t", target, key)
    return result.returncode == 0


def capture_recent_pane(tmux_socket: str, target: str) -> str | None:
    result = run_tmux_command(
        tmux_socket, "capture-pane", "-t", target, "-p", "-S", "-10"
    )
    return result.stdout if result.returncode == 0 else None


def build_paste_buffer_name(target: str) -> str:
    return f"heartbeat-paste-{target.replace(':', '-')}"


def send_prompt_via_tmux_buffer(tmux_socket: str, target: str, content: str) -> bool:
    buffer_name = build_paste_buffer_name(target)

    with tempfile.NamedTemporaryFile(
        mode="w",
        prefix="heartbeat-prompt-",
        suffix=".md",
        delete=False,
    ) as temporary_file:
        temporary_file.write(content)
        temporary_file_path = temporary_file.name

    try:
        load_result = run_tmux_command(
            tmux_socket, "load-buffer", "-b", buffer_name, temporary_file_path
        )
        if load_result.returncode != 0:
            print(
                f"Error loading buffer: {load_result.stderr.strip()}", file=sys.stderr
            )
            return False

        paste_result = run_tmux_command(
            tmux_socket, "paste-buffer", "-b", buffer_name, "-t", target
        )
        if paste_result.returncode != 0:
            print(
                f"Error pasting buffer: {paste_result.stderr.strip()}", file=sys.stderr
            )
            return False

        run_tmux_command(tmux_socket, "send-keys", "-t", target, "Enter")
        run_tmux_command(tmux_socket, "delete-buffer", "-b", buffer_name)
        return True
    finally:
        os.unlink(temporary_file_path)


class TmuxPaneHandle:
    def __init__(self, tmux_socket: str, target: str):
        self.tmux_socket = tmux_socket
        self.target = target


class TmuxHeartbeatBackend(HeartbeatMultiplexerBackend):
    def prepare_pane_handle(
        self, session_name: str, window_name: str
    ) -> TmuxPaneHandle | None:
        tmux_socket = find_tmux_socket()
        if not tmux_socket:
            return None
        return TmuxPaneHandle(tmux_socket, f"{session_name}:{window_name}")

    def capture_recent_pane(self, pane_handle: TmuxPaneHandle) -> str | None:
        return capture_recent_pane(pane_handle.tmux_socket, pane_handle.target)

    def send_single_key_to_pane(self, pane_handle: TmuxPaneHandle, key: str) -> bool:
        return send_single_key_to_pane(pane_handle.tmux_socket, pane_handle.target, key)

    def send_prompt_to_pane(self, pane_handle: TmuxPaneHandle, content: str) -> bool:
        return send_prompt_via_tmux_buffer(
            pane_handle.tmux_socket, pane_handle.target, content
        )
