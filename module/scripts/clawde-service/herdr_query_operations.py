import json
import subprocess
import sys


class HerdrQueryOperations:
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
            session.get("running") for session in session_list.get("sessions", [])
        )

    def find_workspace_id_for_label(self, workspace_label: str) -> str | None:
        result = self.run_herdr_command("workspace", "list")
        if result.returncode != 0:
            return None
        workspace_list = self.parse_herdr_json(result.stdout)
        if workspace_list is None:
            return None
        return next(
            (
                workspace["workspace_id"]
                for workspace in workspace_list.get("result", {}).get("workspaces", [])
                if workspace.get("label") == workspace_label
            ),
            None,
        )

    def create_workspace(self, workspace_label: str) -> str | None:
        result = self.run_herdr_command(
            "workspace", "create", "--label", workspace_label, "--no-focus"
        )
        if result.returncode != 0:
            print(
                f"Error: failed to create herdr workspace {workspace_label!r}: "
                f"{result.stderr.strip()}",
                file=sys.stderr,
            )
            return None
        created = self.parse_herdr_json(result.stdout)
        if created is None:
            return None
        return created.get("result", {}).get("workspace", {}).get("workspace_id")

    def list_workspace_tabs(self, workspace_id: str) -> list | None:
        result = self.run_herdr_command("tab", "list", "--workspace", workspace_id)
        if result.returncode != 0:
            return None
        tab_list = self.parse_herdr_json(result.stdout)
        if tab_list is None:
            return None
        return tab_list.get("result", {}).get("tabs", [])

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
