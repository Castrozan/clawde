import json
import subprocess

from a2a_server.backends import herdr_pane_resolution


class FakeHerdrFleet:
    def __init__(self) -> None:
        self.workspaces: list[dict] = []
        self.tabs: list[dict] = []
        self.panes: list[dict] = []
        self.pane_text_by_pane_id: dict[str, str] = {}
        self.invocations: list[list[str]] = []

    def with_agent_pane(
        self,
        pane_id: str,
        tab_label: str | None = None,
        workspace_label: str = "clawde",
        agent: str | None = "claude",
        agent_status: str = "idle",
        cwd: str | None = None,
    ) -> "FakeHerdrFleet":
        workspace_id = f"ws-of-{workspace_label}"
        tab_id = f"tab-of-{pane_id}"
        self._remember_workspace(workspace_id, workspace_label)
        self.tabs.append(
            {"tab_id": tab_id, "label": tab_label, "workspace_id": workspace_id}
        )
        pane = {"pane_id": pane_id, "tab_id": tab_id, "agent_status": agent_status}
        if agent is not None:
            pane["agent"] = agent
        if cwd is not None:
            pane["cwd"] = cwd
        self.panes.append(pane)
        return self

    def showing(self, pane_text: str, pane_id: str | None = None) -> "FakeHerdrFleet":
        for pane in self.panes:
            if pane_id is None or pane["pane_id"] == pane_id:
                self.pane_text_by_pane_id[pane["pane_id"]] = pane_text
        return self

    def with_pane_removed(self, pane_id: str) -> "FakeHerdrFleet":
        self.panes = [pane for pane in self.panes if pane["pane_id"] != pane_id]
        return self

    def with_agent_status(self, pane_id: str, agent_status: str) -> "FakeHerdrFleet":
        for pane in self.panes:
            if pane["pane_id"] == pane_id:
                pane["agent_status"] = agent_status
        return self

    def install_into(self, monkeypatch) -> "FakeHerdrFleet":
        monkeypatch.setattr(
            herdr_pane_resolution, "run_herdr_command", self.run_command
        )
        return self

    def invocations_matching(self, prefix: list[str]) -> list[list[str]]:
        return [
            invocation
            for invocation in self.invocations
            if invocation[: len(prefix)] == prefix
        ]

    def run_command(self, arguments: list[str]) -> subprocess.CompletedProcess:
        self.invocations.append(arguments)
        if arguments[:2] == ["workspace", "list"]:
            return self._json_result({"workspaces": self.workspaces})
        if arguments[:2] == ["tab", "list"]:
            return self._json_result({"tabs": self._tabs_selected_by(arguments)})
        if arguments[:2] == ["pane", "list"]:
            return self._json_result({"panes": self.panes})
        if arguments[:2] == ["pane", "get"]:
            return self._pane_get_result(arguments[2])
        if arguments[:2] == ["pane", "read"]:
            return self._completed(0, self.pane_text_by_pane_id.get(arguments[2], ""))
        return self._completed(0, "")

    def _remember_workspace(self, workspace_id: str, workspace_label: str) -> None:
        if any(
            workspace["workspace_id"] == workspace_id for workspace in self.workspaces
        ):
            return
        self.workspaces.append({"workspace_id": workspace_id, "label": workspace_label})

    def _tabs_selected_by(self, arguments: list[str]) -> list[dict]:
        if "--workspace" not in arguments:
            return self.tabs
        workspace_id = arguments[arguments.index("--workspace") + 1]
        return [tab for tab in self.tabs if tab["workspace_id"] == workspace_id]

    def _pane_get_result(self, pane_id: str) -> subprocess.CompletedProcess:
        pane = next(
            (pane for pane in self.panes if pane["pane_id"] == pane_id),
            None,
        )
        if pane is None:
            return self._completed(1, "")
        return self._json_result({"pane": pane})

    def _json_result(self, result: dict) -> subprocess.CompletedProcess:
        return self._completed(0, json.dumps({"result": result}))

    @staticmethod
    def _completed(returncode: int, stdout: str) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            args=["herdr"], returncode=returncode, stdout=stdout, stderr=""
        )
