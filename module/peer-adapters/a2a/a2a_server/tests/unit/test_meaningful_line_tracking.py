import re

from a2a_server.backends.meaningful_line_tracking import MeaningfulLineTracker


class TestOccurrenceKeysInCaptureOrder:
    def test_yields_one_key_per_non_empty_line_with_occurrence_index_zero_when_unique(
        self,
    ):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        capture = "first line\nsecond line\nthird line\n"
        yielded = list(tracker.occurrence_keys_in_capture_order(capture))
        assert yielded == [("first line", 0), ("second line", 0), ("third line", 0)]

    def test_skips_blank_and_whitespace_only_lines(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        capture = "alpha\n\n   \nbeta\n\t\ngamma\n"
        yielded = list(tracker.occurrence_keys_in_capture_order(capture))
        assert yielded == [("alpha", 0), ("beta", 0), ("gamma", 0)]

    def test_assigns_incrementing_occurrence_indices_to_repeated_lines(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        capture = "same line\nsame line\n  same line  \nunique line\n"
        yielded = list(tracker.occurrence_keys_in_capture_order(capture))
        assert yielded == [
            ("same line", 0),
            ("same line", 1),
            ("same line", 2),
            ("unique line", 0),
        ]

    def test_includes_only_lines_matching_meaningful_pattern_when_set(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=re.compile(r"^⏺ "))
        capture = (
            "❯ user prompt\n⏺ assistant response one\n"
            "  Haiku 4.5 │ ctx 21% │ lim 19% 3h17m\n"
            "⏺ assistant response two\n✻ Cogitated for 6s\n"
        )
        yielded = list(tracker.occurrence_keys_in_capture_order(capture))
        assert yielded == [
            ("⏺ assistant response one", 0),
            ("⏺ assistant response two", 0),
        ]

    def test_pattern_matching_uses_normalized_stripped_form(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=re.compile(r"^⏺ "))
        capture = "    ⏺ leading whitespace response\n"
        yielded = list(tracker.occurrence_keys_in_capture_order(capture))
        assert yielded == [("⏺ leading whitespace response", 0)]

    def test_returns_empty_for_empty_capture(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        assert list(tracker.occurrence_keys_in_capture_order("")) == []

    def test_assigns_independent_occurrence_counters_per_line_value(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        capture = "alpha\nbeta\nalpha\ngamma\nbeta\ndelta\n"
        yielded = list(tracker.occurrence_keys_in_capture_order(capture))
        assert yielded == [
            ("alpha", 0),
            ("beta", 0),
            ("alpha", 1),
            ("gamma", 0),
            ("beta", 1),
            ("delta", 0),
        ]


class TestLinesAppearingSinceThePreviousCapture:
    def test_reports_every_line_when_nothing_has_been_observed_yet(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        assert tracker.lines_appearing_since_the_previous_capture("alpha\nbeta\n") == [
            "alpha",
            "beta",
        ]

    def test_reports_nothing_for_a_capture_adopted_as_the_baseline(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        tracker.adopt_capture_as_baseline("alpha\nbeta\n")
        assert tracker.lines_appearing_since_the_previous_capture("alpha\nbeta\n") == []

    def test_reports_only_the_lines_added_since_the_previous_capture(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        tracker.adopt_capture_as_baseline("alpha\n")
        assert tracker.lines_appearing_since_the_previous_capture(
            "alpha\nbeta\ngamma\n"
        ) == ["beta", "gamma"]

    def test_reports_a_repeated_line_again_because_occurrences_are_counted(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        tracker.adopt_capture_as_baseline("same\n")
        assert tracker.lines_appearing_since_the_previous_capture("same\nsame\n") == [
            "same"
        ]

    def test_reports_every_line_again_after_forgetting_what_was_observed(self):
        tracker = MeaningfulLineTracker(meaningful_line_pattern=None)
        tracker.adopt_capture_as_baseline("alpha\nbeta\n")
        tracker.forget_everything_observed_so_far()
        assert tracker.lines_appearing_since_the_previous_capture("alpha\nbeta\n") == [
            "alpha",
            "beta",
        ]
