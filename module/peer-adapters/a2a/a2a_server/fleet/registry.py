import threading

from .agent_metadata import FleetAgentMetadata
from .discovery import DiscoveredAgentPane
from .naming import unique_peer_names_by_pane_id
from .session import AttachedAgentSession


class AttachedAgentRegistry:
    def __init__(self, metadata: FleetAgentMetadata, daemon_base_url: str) -> None:
        self._metadata = metadata
        self._daemon_base_url = daemon_base_url
        self._sessions_by_peer_name: dict[str, AttachedAgentSession] = {}
        self._lock = threading.Lock()

    def session_named(self, peer_name: str) -> AttachedAgentSession | None:
        with self._lock:
            return self._sessions_by_peer_name.get(peer_name)

    def every_session(self) -> list[AttachedAgentSession]:
        with self._lock:
            return list(self._sessions_by_peer_name.values())

    def reconcile_against_the_live_fleet(
        self,
        panes: list[DiscoveredAgentPane],
        tab_labels_by_tab_id: dict[str, str],
    ) -> None:
        if not panes:
            return
        peer_name_by_pane_id = unique_peer_names_by_pane_id(panes, tab_labels_by_tab_id)
        pane_by_peer_name = {peer_name_by_pane_id[pane.pane_id]: pane for pane in panes}
        for session in self._sessions_no_longer_backed_by_a_pane(pane_by_peer_name):
            self._retire_session(session)
        for peer_name, pane in pane_by_peer_name.items():
            self._adopt_pane_if_not_already_attached(peer_name, pane)

    def _sessions_no_longer_backed_by_a_pane(
        self, pane_by_peer_name: dict[str, DiscoveredAgentPane]
    ) -> list[AttachedAgentSession]:
        with self._lock:
            return [
                session
                for peer_name, session in self._sessions_by_peer_name.items()
                if peer_name not in pane_by_peer_name
                or pane_by_peer_name[peer_name].pane_id != session.pane_id
            ]

    def _retire_session(self, session: AttachedAgentSession) -> None:
        with self._lock:
            if self._sessions_by_peer_name.get(session.peer_name) is session:
                del self._sessions_by_peer_name[session.peer_name]
        session.stop()

    def _adopt_pane_if_not_already_attached(
        self, peer_name: str, pane: DiscoveredAgentPane
    ) -> None:
        with self._lock:
            already_attached = self._sessions_by_peer_name.get(peer_name)
            if (
                already_attached is not None
                and already_attached.pane_id == pane.pane_id
            ):
                return
        adopted_session = AttachedAgentSession(
            peer_name, pane, self._metadata, self._daemon_base_url
        )
        adopted_session.start()
        with self._lock:
            self._sessions_by_peer_name[peer_name] = adopted_session
