import re

from a2a_server.backends.herdr_backend import HerdrAttachedAgentBackend
from fake_herdr_fleet import FakeHerdrFleet


def attached_backend(fleet, monkeypatch, meaningful_line_pattern=None):
    fleet.install_into(monkeypatch)
    backend = HerdrAttachedAgentBackend(
        "w1:p9", meaningful_line_pattern=meaningful_line_pattern
    )
    backend.start()
    return backend


class TestObserveReportsNewMeaningfulLines:
    def test_reports_nothing_while_the_pane_has_not_changed(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny")
        fleet.showing("⏺ first response\n")
        backend = attached_backend(fleet, monkeypatch, re.compile(r"^⏺ "))
        assert backend.observe().raw_output_since_last_call == ""

    def test_reports_only_the_lines_that_appeared_since_the_previous_capture(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny")
        fleet.showing("⏺ first response\n")
        backend = attached_backend(fleet, monkeypatch, re.compile(r"^⏺ "))
        fleet.showing("⏺ first response\n⏺ second response\n")
        assert backend.observe().raw_output_since_last_call == "⏺ second response"

    def test_ignores_status_line_noise_that_changes_between_captures(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny")
        fleet.showing("⏺ first response\n  ctx 21% │ lim 19% 3h17m\n")
        backend = attached_backend(fleet, monkeypatch, re.compile(r"^⏺ "))
        fleet.showing("⏺ first response\n  ctx 24% │ lim 20% 3h11m\n")
        assert backend.observe().raw_output_since_last_call == ""


class TestObserveReportsWhetherTheAgentIsAlive:
    def test_a_pane_running_a_harness_is_alive(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny")
        assert attached_backend(fleet, monkeypatch).observe().is_alive is True

    def test_a_pane_with_no_harness_in_it_is_not_alive(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny", agent=None)
        assert attached_backend(fleet, monkeypatch).observe().is_alive is False


class TestObserveReportsWhetherTheAgentIsBusy:
    def test_a_working_agent_is_busy(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane(
            "w1:p9", tab_label="jenny", agent_status="working"
        )
        assert attached_backend(fleet, monkeypatch).observe().agent_is_busy is True

    def test_a_blocked_agent_is_busy_because_its_turn_has_not_ended(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane(
            "w1:p9", tab_label="jenny", agent_status="blocked"
        )
        assert attached_backend(fleet, monkeypatch).observe().agent_is_busy is True

    def test_an_idle_agent_is_not_busy(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane(
            "w1:p9", tab_label="jenny", agent_status="idle"
        )
        assert attached_backend(fleet, monkeypatch).observe().agent_is_busy is False

    def test_a_status_herdr_calls_unknown_leaves_busyness_unknown_rather_than_idle(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane(
            "w1:p9", tab_label="jenny", agent_status="unknown"
        )
        assert attached_backend(fleet, monkeypatch).observe().agent_is_busy is None

    def test_a_pane_reporting_no_status_at_all_leaves_busyness_unknown(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny")
        fleet.panes[0].pop("agent_status")
        assert attached_backend(fleet, monkeypatch).observe().agent_is_busy is None
