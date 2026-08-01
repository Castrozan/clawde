import re
import time

from . import herdr_pane_resolution
from .base import AgentBackend, BackendObservation
from .meaningful_line_tracking import MeaningfulLineTracker

PANE_CAPTURE_LINE_COUNT = 200
DELAY_BETWEEN_TYPING_INPUT_AND_PRESSING_ENTER_SECONDS = 0.25
AGENT_STATUSES_THAT_MEAN_THE_TURN_IS_STILL_RUNNING = frozenset({"working", "blocked"})
AGENT_STATUSES_THAT_MEAN_THE_TURN_HAS_ENDED = frozenset({"idle"})


def agent_status_means_the_agent_is_busy(agent_status) -> bool | None:
    if agent_status in AGENT_STATUSES_THAT_MEAN_THE_TURN_IS_STILL_RUNNING:
        return True
    if agent_status in AGENT_STATUSES_THAT_MEAN_THE_TURN_HAS_ENDED:
        return False
    return None


class HerdrAttachedAgentBackend(AgentBackend):
    def __init__(
        self,
        workspace_label: str,
        tab_label: str,
        meaningful_line_pattern: re.Pattern | None = None,
    ) -> None:
        self._workspace_label = workspace_label
        self._tab_label = tab_label
        self._meaningful_line_tracker = MeaningfulLineTracker(meaningful_line_pattern)
        self._pane_id_holding_the_agent: str | None = None
        self._last_activity_at_epoch_seconds = time.time()

    def start(self) -> None:
        self._read_agent_pane_information()

    def send_input_text(self, text: str) -> None:
        pane_id = self._read_agent_pane_information().get("pane_id")
        if pane_id is None:
            raise RuntimeError(self._unresolvable_target_description())
        herdr_pane_resolution.send_text_to_pane(pane_id, text)
        time.sleep(DELAY_BETWEEN_TYPING_INPUT_AND_PRESSING_ENTER_SECONDS)
        herdr_pane_resolution.send_key_to_pane(pane_id, "Enter")
        self._last_activity_at_epoch_seconds = time.time()

    def observe(self) -> BackendObservation:
        pane_information = self._read_agent_pane_information()
        pane_id = pane_information.get("pane_id")
        if pane_id is None:
            return BackendObservation(
                raw_output_since_last_call="",
                is_alive=False,
                last_activity_at_epoch_seconds=self._last_activity_at_epoch_seconds,
            )
        new_lines_in_capture_order = (
            self._meaningful_line_tracker.lines_appearing_since_the_previous_capture(
                self._capture_agent_pane_text(pane_id)
            )
        )
        if new_lines_in_capture_order:
            self._last_activity_at_epoch_seconds = time.time()
        return BackendObservation(
            raw_output_since_last_call="\n".join(new_lines_in_capture_order),
            is_alive=pane_information.get("agent") is not None,
            last_activity_at_epoch_seconds=self._last_activity_at_epoch_seconds,
            agent_is_busy=agent_status_means_the_agent_is_busy(
                pane_information.get("agent_status")
            ),
        )

    def cancel_gracefully(self) -> None:
        pane_id = self._read_agent_pane_information().get("pane_id")
        if pane_id is None:
            return
        herdr_pane_resolution.send_key_to_pane(pane_id, "C-c")

    def stop(self) -> None:
        self._detach_leaving_the_wrapped_agent_running()

    def _detach_leaving_the_wrapped_agent_running(self) -> None:
        self._pane_id_holding_the_agent = None
        self._meaningful_line_tracker.forget_everything_observed_so_far()

    def _unresolvable_target_description(self) -> str:
        return (
            f"no herdr pane hosts tab {self._tab_label!r} of workspace "
            f"{self._workspace_label!r}; the backend attaches to an already-running agent"
        )

    def _read_agent_pane_information(self) -> dict:
        information_of_the_remembered_pane = (
            herdr_pane_resolution.read_pane_information(self._pane_id_holding_the_agent)
        )
        if information_of_the_remembered_pane:
            return information_of_the_remembered_pane
        self._pane_id_holding_the_agent = (
            herdr_pane_resolution.find_pane_id_hosting_the_agent_tab(
                self._workspace_label, self._tab_label
            )
        )
        if self._pane_id_holding_the_agent is None:
            return {}
        self._meaningful_line_tracker.adopt_capture_as_baseline(
            self._capture_agent_pane_text(self._pane_id_holding_the_agent)
        )
        return herdr_pane_resolution.read_pane_information(
            self._pane_id_holding_the_agent
        )

    def _capture_agent_pane_text(self, pane_id: str) -> str:
        return herdr_pane_resolution.capture_pane_text(pane_id, PANE_CAPTURE_LINE_COUNT)
