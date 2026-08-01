from ..active_task_coordinator import ActiveTaskCoordinator
from ..agent_card import AgentCard, build_agent_card_from_environment
from ..backends.herdr_backend import HerdrAttachedAgentBackend
from ..task_store import TaskStore
from .agent_metadata import FleetAgentMetadata
from .discovery import DiscoveredAgentPane


class AttachedAgentSession:
    def __init__(
        self,
        peer_name: str,
        pane: DiscoveredAgentPane,
        metadata: FleetAgentMetadata,
        daemon_base_url: str,
    ) -> None:
        self.peer_name = peer_name
        self.pane_id = pane.pane_id
        self.harness = pane.harness
        self.description = metadata.description_for(peer_name, pane.harness)
        self.backend = HerdrAttachedAgentBackend(
            pane.pane_id,
            metadata.meaningful_line_pattern_for(peer_name, pane.harness),
        )
        self.task_store = TaskStore()
        self.coordinator = ActiveTaskCoordinator(self.task_store, self.backend)
        self.agent_card = self._build_agent_card(daemon_base_url)

    def start(self) -> None:
        self.backend.start()

    def stop(self) -> None:
        self.coordinator.fail_active_task_because_the_target_vanished()
        self.backend.stop()

    def is_holding_an_unfinished_task(self) -> bool:
        return self.coordinator.is_holding_an_unfinished_task()

    def to_registry_entry(self) -> dict:
        return {
            "name": self.peer_name,
            "description": self.description,
            "harness": self.harness,
            "paneId": self.pane_id,
            "endpoint": self.agent_card.endpoint_url,
        }

    def _build_agent_card(self, daemon_base_url: str) -> AgentCard:
        return build_agent_card_from_environment(
            self.peer_name,
            self.description,
            f"{daemon_base_url}/agents/{self.peer_name}",
        )
