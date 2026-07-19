import subprocess
import sys
import time

from herdr_query_operations import HerdrQueryOperations
from supervisor_backend_base import (
    MULTIPLEXER_ENVIRONMENT_VARIABLE,
    SupervisorMultiplexerBackend,
)

HERDR_SERVER_STARTUP_WAIT_ATTEMPTS = 30
HERDR_SERVER_STARTUP_WAIT_DELAY_SECONDS = 0.5
HERDR_MULTIPLEXER_ENVIRONMENT_VALUE = "herdr"
HERDR_DEFAULT_WORKSPACE_TAB_LABEL = "1"


class HerdrSupervisorBackend(HerdrQueryOperations, SupervisorMultiplexerBackend):
    def start_headless_herdr_server(self) -> None:
        subprocess.Popen(
            ["herdr", "server"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    def ensure_server_running(self) -> bool:
        if self.herdr_server_is_running():
            return True
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

    def ensure_workspace(self, workspace_label: str) -> str | None:
        existing_workspace_id = self.find_workspace_id_for_label(workspace_label)
        if existing_workspace_id is not None:
            return existing_workspace_id
        return self.create_workspace(workspace_label)

    def find_agent_tab(self, workspace_label: str, agent_name: str) -> dict | None:
        workspace_id = self.find_workspace_id_for_label(workspace_label)
        if workspace_id is None:
            return None
        tabs = self.list_workspace_tabs(workspace_id)
        if tabs is None:
            return None
        return next(
            (tab for tab in tabs if tab.get("label") == agent_name),
            None,
        )

    def agent_window_exists(self, session_name: str, agent_name: str) -> bool:
        return self.find_agent_tab(session_name, agent_name) is not None

    def run_wrapper_in_pane(self, pane_id: str, wrapper_command: str) -> bool:
        wrapper_command_with_multiplexer_environment = (
            f"{MULTIPLEXER_ENVIRONMENT_VARIABLE}="
            f"{HERDR_MULTIPLEXER_ENVIRONMENT_VALUE} {wrapper_command}"
        )
        result = self.run_herdr_command(
            "pane", "run", pane_id, wrapper_command_with_multiplexer_environment
        )
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
        workspace_id = self.ensure_workspace(session_name)
        if workspace_id is None:
            return False
        create_result = self.run_herdr_command(
            "tab",
            "create",
            "--workspace",
            workspace_id,
            "--label",
            agent_name,
            "--no-focus",
        )
        if create_result.returncode != 0:
            print(
                f"Error: failed to create herdr tab {agent_name!r} in workspace "
                f"{session_name!r}: {create_result.stderr.strip()}",
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
        tab = self.find_agent_tab(session_name, agent_name)
        if tab is None:
            return self.create_agent_window(session_name, agent_name, wrapper_command)
        pane_id = self.resolve_pane_id_for_tab_id(tab["tab_id"])
        if pane_id is None:
            return self.create_agent_window(session_name, agent_name, wrapper_command)
        return self.run_wrapper_in_pane(pane_id, wrapper_command)

    def ensure_host_ready(self, session_name: str) -> bool:
        if not self.ensure_server_running():
            return False
        if self.find_workspace_id_for_label(session_name) is not None:
            return False
        return self.create_workspace(session_name) is not None

    def remove_bootstrap_scaffolding(self, session_name: str) -> None:
        workspace_id = self.find_workspace_id_for_label(session_name)
        if workspace_id is None:
            return
        tabs = self.list_workspace_tabs(workspace_id)
        if tabs is None or len(tabs) <= 1:
            return
        bootstrap_tab = next(
            (
                tab
                for tab in tabs
                if tab.get("label") == HERDR_DEFAULT_WORKSPACE_TAB_LABEL
            ),
            None,
        )
        if bootstrap_tab is None:
            return
        self.run_herdr_command("tab", "close", bootstrap_tab["tab_id"])

    def remove_agent_window(self, session_name: str, agent_name: str) -> None:
        tab = self.find_agent_tab(session_name, agent_name)
        if tab is None:
            return
        self.run_herdr_command("tab", "close", tab["tab_id"])
