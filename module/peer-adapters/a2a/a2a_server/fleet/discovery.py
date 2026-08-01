import dataclasses

from ..backends import herdr_pane_resolution


@dataclasses.dataclass(frozen=True)
class DiscoveredAgentPane:
    pane_id: str
    tab_id: str
    harness: str
    agent_status: str | None
    working_directory: str | None


def read_agent_panes_from_the_live_fleet() -> list[DiscoveredAgentPane]:
    panes = herdr_pane_resolution.read_herdr_result(["pane", "list"]).get("panes", [])
    return [
        DiscoveredAgentPane(
            pane_id=pane["pane_id"],
            tab_id=pane.get("tab_id") or "",
            harness=pane["agent"],
            agent_status=pane.get("agent_status"),
            working_directory=pane.get("cwd"),
        )
        for pane in panes
        if pane.get("agent") and pane.get("pane_id")
    ]


def read_tab_labels_by_tab_id() -> dict[str, str]:
    tabs = herdr_pane_resolution.read_herdr_result(["tab", "list"]).get("tabs", [])
    return {
        tab["tab_id"]: tab["label"]
        for tab in tabs
        if tab.get("tab_id") and tab.get("label")
    }
