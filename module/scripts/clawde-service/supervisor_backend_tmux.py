import subprocess
import sys

from supervisor_backend_base import (
    BOOTSTRAP_PLACEHOLDER_WINDOW_NAME,
    SupervisorMultiplexerBackend,
)


class TmuxSupervisorBackend(SupervisorMultiplexerBackend):
    def run_tmux_command(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["tmux", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def session_exists(self, session_name: str) -> bool:
        return self.run_tmux_command("has-session", "-t", session_name).returncode == 0

    def ensure_host_ready(self, session_name: str) -> bool:
        if self.session_exists(session_name):
            return False
        result = self.run_tmux_command(
            "new-session",
            "-d",
            "-s",
            session_name,
            "-n",
            BOOTSTRAP_PLACEHOLDER_WINDOW_NAME,
            "sleep infinity",
        )
        if result.returncode == 0:
            return True
        if self.session_exists(session_name):
            return False
        print(
            f"Error: failed to create tmux session {session_name!r}: {result.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    def agent_window_exists(self, session_name: str, agent_name: str) -> bool:
        result = self.run_tmux_command(
            "list-windows", "-t", session_name, "-F", "#{window_name}"
        )
        if result.returncode != 0:
            return False
        return agent_name in result.stdout.splitlines()

    def create_agent_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        result = self.run_tmux_command(
            "new-window", "-t", session_name, "-n", agent_name, wrapper_command
        )
        if result.returncode != 0:
            print(
                f"Error: failed to create tmux window {agent_name!r}: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        return True

    def relaunch_wrapper_in_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        result = self.run_tmux_command(
            "respawn-window",
            "-k",
            "-t",
            f"{session_name}:{agent_name}",
            wrapper_command,
        )
        if result.returncode != 0:
            print(
                f"Error: failed to relaunch wrapper in tmux window {agent_name!r}: "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        return True

    def remove_bootstrap_scaffolding(self, session_name: str) -> None:
        self.run_tmux_command(
            "kill-window", "-t", f"{session_name}:{BOOTSTRAP_PLACEHOLDER_WINDOW_NAME}"
        )

    def remove_agent_window(self, session_name: str, agent_name: str) -> None:
        self.run_tmux_command("kill-window", "-t", f"{session_name}:{agent_name}")
