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
        workspace_label: str,
        tab_label: str,
        pane_id: str,
        agent: str | None = "claude",
        agent_status: str = "idle",
    ) -> "FakeHerdrFleet":
        workspace_id = f"ws-of-{workspace_label}"
        tab_id = f"tab-of-{pane_id}"
        self.workspaces = [{"workspace_id": workspace_id, "label": workspace_label}]
        self.tabs = [
            {"tab_id": tab_id, "label": tab_label, "workspace_id": workspace_id}
        ]
        pane = {"pane_id": pane_id, "tab_id": tab_id, "agent_status": agent_status}
        if agent is not None:
            pane["agent"] = agent
        self.panes = [pane]
        return self

    def showing(self, pane_text: str) -> "FakeHerdrFleet":
        for pane in self.panes:
            self.pane_text_by_pane_id[pane["pane_id"]] = pane_text
        return self

    def install_into(self, monkeypatch) -> "FakeHerdrFleet":
        monkeypatch.setattr(
            herdr_pane_resolution, "run_herdr_command", self.run_command
        )
        return self

    def run_command(self, arguments: list[str]) -> subprocess.CompletedProcess:
        self.invocations.append(arguments)
        if arguments[:2] == ["workspace", "list"]:
            return self._json_result({"workspaces": self.workspaces})
        if arguments[:2] == ["tab", "list"]:
            return self._json_result({"tabs": self._tabs_of_workspace(arguments[-1])})
        if arguments[:2] == ["pane", "list"]:
            return self._json_result({"panes": self.panes})
        if arguments[:2] == ["pane", "get"]:
            return self._pane_get_result(arguments[2])
        if arguments[:2] == ["pane", "read"]:
            return self._completed(0, self.pane_text_by_pane_id.get(arguments[2], ""))
        return self._completed(0, "")

    def _tabs_of_workspace(self, workspace_id: str) -> list[dict]:
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
