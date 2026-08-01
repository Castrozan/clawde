import dataclasses
import re


@dataclasses.dataclass(frozen=True)
class CaptureDifference:
    settled_lines: list[str]
    the_pane_produced_something_new: bool


class MeaningfulLineTracker:
    def __init__(self, meaningful_line_pattern: re.Pattern | None = None) -> None:
        self._meaningful_line_pattern = meaningful_line_pattern
        self._previously_observed_occurrence_keys: set[tuple[str, int]] = set()
        self._occurrence_keys_awaiting_confirmation: list[tuple[str, int]] = []

    def adopt_capture_as_baseline(self, capture_text: str) -> None:
        self._previously_observed_occurrence_keys = set(
            self.occurrence_keys_in_capture_order(capture_text)
        )
        self._occurrence_keys_awaiting_confirmation = []

    def forget_everything_observed_so_far(self) -> None:
        self._previously_observed_occurrence_keys = set()
        self._occurrence_keys_awaiting_confirmation = []

    def difference_since_the_previous_capture(
        self, capture_text: str
    ) -> CaptureDifference:
        occurrence_keys_in_order = list(
            self.occurrence_keys_in_capture_order(capture_text)
        )
        occurrence_keys_as_set = set(occurrence_keys_in_order)
        lines_that_are_still_on_screen = [
            line
            for (line, occurrence_index) in self._occurrence_keys_awaiting_confirmation
            if (line, occurrence_index) in occurrence_keys_as_set
        ]
        newly_appeared_occurrence_keys = (
            occurrence_keys_as_set - self._previously_observed_occurrence_keys
        )
        self._occurrence_keys_awaiting_confirmation = [
            occurrence_key
            for occurrence_key in occurrence_keys_in_order
            if occurrence_key in newly_appeared_occurrence_keys
        ]
        self._previously_observed_occurrence_keys = occurrence_keys_as_set
        return CaptureDifference(
            settled_lines=lines_that_are_still_on_screen,
            the_pane_produced_something_new=bool(newly_appeared_occurrence_keys)
            or bool(lines_that_are_still_on_screen),
        )

    def occurrence_keys_in_capture_order(self, capture_text: str):
        per_line_occurrence_counters: dict[str, int] = {}
        for raw_line in capture_text.splitlines():
            normalized = raw_line.strip()
            if not normalized:
                continue
            if (
                self._meaningful_line_pattern is not None
                and not self._meaningful_line_pattern.search(normalized)
            ):
                continue
            occurrence_index_for_this_line = per_line_occurrence_counters.get(
                normalized, 0
            )
            yield (normalized, occurrence_index_for_this_line)
            per_line_occurrence_counters[normalized] = (
                occurrence_index_for_this_line + 1
            )
