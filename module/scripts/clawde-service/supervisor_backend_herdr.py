import json
import subprocess
import sys
import time

from supervisor_backend_base import SupervisorMultiplexerBackend

HERDR_SERVER_STARTUP_WAIT_ATTEMPTS = 30
HERDR_SERVER_STARTUP_WAIT_DELAY_SECONDS = 0.5


class HerdrSupervisorBackend(SupervisorMultiplexerBackend):
    def run_herdr_command(self, *arguments: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["herdr", *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def parse_herdr_json(self, stdout: str) -> dict | None:
        try:
            return json.loads(stdout)
        except (ValueError, TypeError):
            return None

    def herdr_server_is_running(self) -> bool:
        result = self.run_herdr_command("session", "list", "--json")
        if result.returncode != 0:
            return False
        session_list = self.parse_herdr_json(result.stdout)
        if session_list is None:
            return False
        return any(
            session.get("running")
            for session in session_list.get("result", {}).get("sessions", [])
        )

    def start_headless_herdr_server(self) -> None:
        subprocess.Popen(
            ["herdr", "server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    def ensure_host_ready(self, session_name: str) -> bool:
        if self.herdr_server_is_running():
            return False
        self.start_headless_herdr_server()
        for _ in range(HERDR_SERVER_STARTUP_WAIT_ATTEMPTS):
            if self.herdr_server_is_running():
                return True
            time.sleep(HERDR_SERVER_STARTUP_WAIT_DELAY_SECONDS)
        print(
            "Error: herdr server did not come up after starting it headlessly",
            file=sys.stderr,
        )
        return False

    def find_agent_tab(self, agent_name: str) -> dict | None:
        result = self.run_herdr_command("tab", "list")
        if result.returncode != 0:
            return None
        tab_list = self.parse_herdr_json(result.stdout)
        if tab_list is None:
            return None
        return next(
            (
                tab
                for tab in tab_list.get("result", {}).get("tabs", [])
                if tab.get("label") == agent_name
            ),
            None,
        )

    def resolve_pane_id_for_tab_id(self, tab_id: str) -> str | None:
        result = self.run_herdr_command("pane", "list")
        if result.returncode != 0:
            return None
        pane_list = self.parse_herdr_json(result.stdout)
        if pane_list is None:
            return None
        return next(
            (
                pane["pane_id"]
                for pane in pane_list.get("result", {}).get("panes", [])
                if pane.get("tab_id") == tab_id
            ),
            None,
        )

    def agent_window_exists(self, session_name: str, agent_name: str) -> bool:
        return self.find_agent_tab(agent_name) is not None

    def run_wrapper_in_pane(self, pane_id: str, wrapper_command: str) -> bool:
        result = self.run_herdr_command("pane", "run", pane_id, wrapper_command)
        if result.returncode != 0:
            print(
                f"Error: failed to run wrapper in herdr pane {pane_id!r}: "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        return True

    def create_agent_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        create_result = self.run_herdr_command(
            "tab", "create", "--label", agent_name, "--no-focus"
        )
        if create_result.returncode != 0:
            print(
                f"Error: failed to create herdr tab {agent_name!r}: "
                f"{create_result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        created = self.parse_herdr_json(create_result.stdout)
        if created is None:
            return False
        pane_id = created.get("result", {}).get("root_pane", {}).get("pane_id")
        if not pane_id:
            return False
        return self.run_wrapper_in_pane(pane_id, wrapper_command)

    def relaunch_wrapper_in_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        tab = self.find_agent_tab(agent_name)
        if tab is None:
            return self.create_agent_window(session_name, agent_name, wrapper_command)
        pane_id = self.resolve_pane_id_for_tab_id(tab["tab_id"])
        if pane_id is None:
            return self.create_agent_window(session_name, agent_name, wrapper_command)
        return self.run_wrapper_in_pane(pane_id, wrapper_command)

    def remove_bootstrap_scaffolding(self, session_name: str) -> None:
        return None
