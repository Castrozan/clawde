import pytest
from a2a_server.backends.herdr_backend import HerdrAttachedAgentBackend
from fake_herdr_fleet import FakeHerdrFleet


@pytest.fixture(autouse=True)
def _no_delay_between_typing_and_enter(monkeypatch):
    monkeypatch.setattr("a2a_server.backends.herdr_backend.time.sleep", lambda _: None)


def commands_sent_to_the_pane(fleet):
    return [
        invocation
        for invocation in fleet.invocations
        if invocation[:2] in (["pane", "send-text"], ["pane", "send-keys"])
    ]


def fleet_hosting_jenny(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane("w1:p9", tab_label="jenny")
    fleet.install_into(monkeypatch)
    return fleet


class TestSendInputText:
    def test_types_the_text_and_then_presses_enter(self, monkeypatch):
        fleet = fleet_hosting_jenny(monkeypatch)
        HerdrAttachedAgentBackend("w1:p9").send_input_text("ping")
        assert commands_sent_to_the_pane(fleet) == [
            ["pane", "send-text", "w1:p9", "ping"],
            ["pane", "send-keys", "w1:p9", "Enter"],
        ]


class TestCancelGracefully:
    def test_interrupts_the_agent_pane(self, monkeypatch):
        fleet = fleet_hosting_jenny(monkeypatch)
        HerdrAttachedAgentBackend("w1:p9").cancel_gracefully()
        assert commands_sent_to_the_pane(fleet) == [
            ["pane", "send-keys", "w1:p9", "C-c"]
        ]


class TestStop:
    def test_never_closes_the_pane_it_only_attached_to(self, monkeypatch):
        fleet = fleet_hosting_jenny(monkeypatch)
        backend = HerdrAttachedAgentBackend("w1:p9")
        backend.start()
        fleet.invocations.clear()
        backend.stop()
        assert fleet.invocations == []


class TestAPaneThatWentAway:
    def test_observe_reports_the_agent_gone_rather_than_raising(self, monkeypatch):
        fleet = fleet_hosting_jenny(monkeypatch)
        backend = HerdrAttachedAgentBackend("w1:p9")
        backend.start()
        fleet.with_pane_removed("w1:p9")
        assert backend.observe().is_alive is False

    def test_observe_never_captures_text_from_a_pane_that_is_gone(self, monkeypatch):
        fleet = fleet_hosting_jenny(monkeypatch)
        backend = HerdrAttachedAgentBackend("w1:p9")
        backend.start()
        fleet.with_pane_removed("w1:p9")
        fleet.invocations.clear()
        backend.observe()
        assert fleet.invocations_matching(["pane", "read"]) == []
