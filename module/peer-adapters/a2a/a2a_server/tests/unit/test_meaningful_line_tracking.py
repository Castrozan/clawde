import re

from a2a_server.backends.meaningful_line_tracking import MeaningfulLineTracker

CLAUDE_RESPONSE_MARKER = re.compile(r"^⏺ ")


def tracker_baselined_on(capture_text: str, pattern=CLAUDE_RESPONSE_MARKER):
    tracker = MeaningfulLineTracker(pattern)
    tracker.adopt_capture_as_baseline(capture_text)
    return tracker


def settled(tracker, capture_text: str) -> list[str]:
    return tracker.difference_since_the_previous_capture(capture_text).settled_lines


def produced_something(tracker, capture_text: str) -> bool:
    return tracker.difference_since_the_previous_capture(
        capture_text
    ).the_pane_produced_something_new


class TestALineIsOutputOnlyOnceItStopsChanging:
    def test_a_line_still_on_screen_one_capture_later_is_reported(self):
        tracker = tracker_baselined_on("")
        assert settled(tracker, "⏺ the answer\n") == []
        assert settled(tracker, "⏺ the answer\n") == ["⏺ the answer"]

    def test_a_line_replaced_before_the_next_capture_is_never_reported(self):
        tracker = tracker_baselined_on("")
        settled(tracker, "⏺ Listing 1 directory · 4m 19s…\n")
        assert settled(tracker, "⏺ Listing 1 directory · 4m 21s…\n") == []

    def test_a_spinner_never_leaks_into_the_answer_it_precedes(self):
        tracker = tracker_baselined_on("")
        for elapsed in ["4m 19s", "4m 21s", "4m 29s"]:
            settled(tracker, f"⏺ Listing 1 directory · {elapsed}…\n")
        settled(tracker, "⏺ Listing 1 directory · 4m 29s…\n⏺ LIVE-OK\n")
        assert settled(tracker, "⏺ LIVE-OK\n") == ["⏺ LIVE-OK"]

    def test_a_settled_line_is_reported_once_and_never_again(self):
        tracker = tracker_baselined_on("")
        settled(tracker, "⏺ the answer\n")
        assert settled(tracker, "⏺ the answer\n") == ["⏺ the answer"]
        assert settled(tracker, "⏺ the answer\n") == []

    def test_settled_lines_come_back_in_the_order_the_pane_shows_them(self):
        tracker = tracker_baselined_on("")
        settled(tracker, "⏺ first\n⏺ second\n")
        assert settled(tracker, "⏺ first\n⏺ second\n") == ["⏺ first", "⏺ second"]

    def test_a_repeated_line_is_reported_once_per_occurrence(self):
        tracker = tracker_baselined_on("")
        settled(tracker, "⏺ same\n⏺ same\n")
        assert settled(tracker, "⏺ same\n⏺ same\n") == ["⏺ same", "⏺ same"]


class TestTheActivityClockFollowsAnyChangeNotJustSettledOutput:
    def test_a_spinner_tick_counts_as_the_pane_being_alive(self):
        tracker = tracker_baselined_on("")
        assert produced_something(tracker, "⏺ Listing · 4m 19s…\n") is True
        assert produced_something(tracker, "⏺ Listing · 4m 21s…\n") is True

    def test_an_unchanged_pane_counts_as_quiet(self):
        tracker = tracker_baselined_on("⏺ the answer\n")
        assert produced_something(tracker, "⏺ the answer\n") is False


class TestWhatCountsAsAMeaningfulLineAtAll:
    def test_the_baseline_is_never_reported_as_output(self):
        tracker = tracker_baselined_on("⏺ said before the task started\n")
        assert settled(tracker, "⏺ said before the task started\n") == []

    def test_lines_that_do_not_match_the_pattern_are_ignored_entirely(self):
        tracker = tracker_baselined_on("")
        settled(tracker, "  ctx 21% | lim 19% 3h17m\n")
        assert settled(tracker, "  ctx 24% | lim 20% 3h11m\n") == []

    def test_with_no_pattern_every_non_empty_line_is_meaningful(self):
        tracker = tracker_baselined_on("", pattern=None)
        settled(tracker, "a plain line\n")
        assert settled(tracker, "a plain line\n") == ["a plain line"]

    def test_forgetting_makes_the_next_capture_a_fresh_baseline(self):
        tracker = tracker_baselined_on("")
        settled(tracker, "⏺ the answer\n")
        tracker.forget_everything_observed_so_far()
        settled(tracker, "⏺ the answer\n")
        assert settled(tracker, "⏺ the answer\n") == ["⏺ the answer"]
