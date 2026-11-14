import sys

from herdr_query_operations import HerdrQueryOperations
from supervisor_backend_base import (
    MULTIPLEXER_ENVIRONMENT_VARIABLE,
    SupervisorMultiplexerBackend,
)

HERDR_MULTIPLEXER_ENVIRONMENT_VALUE = "herdr"
HERDR_DEFAULT_WORKSPACE_TAB_LABEL = "1"


class HerdrSupervisorBackend(HerdrQueryOperations, SupervisorMultiplexerBackend):
    def ensure_server_running(self) -> bool:
        if self.herdr_server_is_running():
            return True
        print(
            "Error: herdr server must be managed independently and is unavailable",
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
        workspace_was_absent = self.find_workspace_id_for_label(session_name) is None
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
        if workspace_was_absent:
            self.close_default_tab_beside_other_tabs(workspace_id)
        pane_id = created.get("result", {}).get("root_pane", {}).get("pane_id")
        if not pane_id:
            return False
        return self.run_wrapper_in_pane(pane_id, wrapper_command)

    def discard_superseded_tab(
        self, session_name: str, agent_name: str, tab_id: str
    ) -> None:
        close_result = self.run_herdr_command("tab", "close", tab_id)
        if close_result.returncode == 0:
            return
        print(
            f"Error: failed to close the superseded herdr tab {tab_id!r} of "
            f"{agent_name!r} in workspace {session_name!r}: "
            f"{close_result.stderr.strip()}",
            file=sys.stderr,
        )

    def relaunch_wrapper_in_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        superseded_tab = self.find_agent_tab(session_name, agent_name)
        if superseded_tab is None:
            return self.create_agent_window(session_name, agent_name, wrapper_command)
        if not self.create_agent_window(session_name, agent_name, wrapper_command):
            return False
        self.discard_superseded_tab(session_name, agent_name, superseded_tab["tab_id"])
        return True

    def ensure_host_ready(self, session_name: str) -> bool:
        self.ensure_server_running()
        return False

    def close_default_tab_beside_other_tabs(self, workspace_id: str) -> None:
        tabs = self.list_workspace_tabs(workspace_id)
        if tabs is None or len(tabs) <= 1:
            return
        default_tab = next(
            (
                tab
                for tab in tabs
                if tab.get("label") == HERDR_DEFAULT_WORKSPACE_TAB_LABEL
            ),
            None,
        )
        if default_tab is None:
            return
        self.run_herdr_command("tab", "close", default_tab["tab_id"])

    def remove_bootstrap_scaffolding(self, session_name: str) -> None:
        workspace_id = self.find_workspace_id_for_label(session_name)
        if workspace_id is None:
            return
        self.close_default_tab_beside_other_tabs(workspace_id)

    def remove_agent_window(self, session_name: str, agent_name: str) -> None:
        workspace_id = self.find_workspace_id_for_label(session_name)
        if workspace_id is None:
            return
        tabs = self.list_workspace_tabs(workspace_id)
        if tabs is None:
            return
        agent_tab = next((tab for tab in tabs if tab.get("label") == agent_name), None)
        if agent_tab is None:
            return
        if len(tabs) == 1:
            self.run_herdr_command("workspace", "close", workspace_id)
            return
        self.run_herdr_command("tab", "close", agent_tab["tab_id"])
