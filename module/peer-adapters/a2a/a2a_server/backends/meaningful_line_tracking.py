import re


class MeaningfulLineTracker:
    def __init__(self, meaningful_line_pattern: re.Pattern | None = None) -> None:
        self._meaningful_line_pattern = meaningful_line_pattern
        self._previously_observed_occurrence_keys: set[tuple[str, int]] = set()

    def adopt_capture_as_baseline(self, capture_text: str) -> None:
        self._previously_observed_occurrence_keys = set(
            self.occurrence_keys_in_capture_order(capture_text)
        )

    def forget_everything_observed_so_far(self) -> None:
        self._previously_observed_occurrence_keys = set()

    def lines_appearing_since_the_previous_capture(
        self, capture_text: str
    ) -> list[str]:
        occurrence_keys_in_order = list(
            self.occurrence_keys_in_capture_order(capture_text)
        )
        occurrence_keys_as_set = set(occurrence_keys_in_order)
        newly_appeared_occurrence_keys = (
            occurrence_keys_as_set - self._previously_observed_occurrence_keys
        )
        self._previously_observed_occurrence_keys = occurrence_keys_as_set
        return [
            line
            for (line, occurrence_index) in occurrence_keys_in_order
            if (line, occurrence_index) in newly_appeared_occurrence_keys
        ]

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
