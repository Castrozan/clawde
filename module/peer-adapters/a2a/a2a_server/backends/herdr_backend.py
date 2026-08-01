import re
import time

from . import herdr_pane_resolution
from .base import AgentBackend, BackendObservation
from .meaningful_line_tracking import MeaningfulLineTracker

PANE_CAPTURE_LINE_COUNT = 200
DELAY_BETWEEN_TYPING_INPUT_AND_PRESSING_ENTER_SECONDS = 0.25
AGENT_STATUSES_THAT_MEAN_THE_TURN_IS_STILL_RUNNING = frozenset({"working", "blocked"})
AGENT_STATUSES_THAT_MEAN_THE_TURN_HAS_ENDED = frozenset({"idle", "done"})


def agent_status_means_the_agent_is_busy(agent_status) -> bool | None:
    if agent_status in AGENT_STATUSES_THAT_MEAN_THE_TURN_IS_STILL_RUNNING:
        return True
    if agent_status in AGENT_STATUSES_THAT_MEAN_THE_TURN_HAS_ENDED:
        return False
    return None


class HerdrAttachedAgentBackend(AgentBackend):
    def __init__(
        self,
        pane_id: str,
        meaningful_line_pattern: re.Pattern | None = None,
    ) -> None:
        self._pane_id = pane_id
        self._meaningful_line_tracker = MeaningfulLineTracker(meaningful_line_pattern)
        self._last_activity_at_epoch_seconds = time.time()

    def start(self) -> None:
        self._meaningful_line_tracker.adopt_capture_as_baseline(
            self._capture_agent_pane_text()
        )

    def send_input_text(self, text: str) -> None:
        herdr_pane_resolution.send_text_to_pane(self._pane_id, text)
        time.sleep(DELAY_BETWEEN_TYPING_INPUT_AND_PRESSING_ENTER_SECONDS)
        herdr_pane_resolution.send_key_to_pane(self._pane_id, "Enter")
        self._last_activity_at_epoch_seconds = time.time()

    def observe(self) -> BackendObservation:
        pane_information = herdr_pane_resolution.read_pane_information(self._pane_id)
        if not pane_information:
            return BackendObservation(
                raw_output_since_last_call="",
                is_alive=False,
                last_activity_at_epoch_seconds=self._last_activity_at_epoch_seconds,
            )
        new_lines_in_capture_order = (
            self._meaningful_line_tracker.lines_appearing_since_the_previous_capture(
                self._capture_agent_pane_text()
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
        herdr_pane_resolution.send_key_to_pane(self._pane_id, "C-c")

    def stop(self) -> None:
        self._meaningful_line_tracker.forget_everything_observed_so_far()

    def _capture_agent_pane_text(self) -> str:
        return herdr_pane_resolution.capture_pane_text(
            self._pane_id, PANE_CAPTURE_LINE_COUNT
        )
