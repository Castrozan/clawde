import threading

from . import discovery
from .registry import AttachedAgentRegistry

FLEET_OBSERVATION_INTERVAL_SECONDS = 1.0


class FleetObservationLoop:
    def __init__(
        self,
        registry: AttachedAgentRegistry,
        observation_interval_seconds: float = FLEET_OBSERVATION_INTERVAL_SECONDS,
    ) -> None:
        self._registry = registry
        self._observation_interval_seconds = observation_interval_seconds
        self._should_stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_until_stopped, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._should_stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def run_one_pass(self) -> None:
        self._registry.reconcile_against_the_live_fleet(
            discovery.read_agent_panes_from_the_live_fleet(),
            discovery.read_tab_labels_by_tab_id(),
        )
        for session in self._registry.every_session():
            if session.is_holding_an_unfinished_task():
                session.coordinator.observe_once_and_apply_to_active_task()

    def _run_until_stopped(self) -> None:
        while not self._should_stop.wait(self._observation_interval_seconds):
            self.run_one_pass()
