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


class TestSendInputText:
    def test_types_the_text_and_then_presses_enter(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.send_input_text("ping")
        assert commands_sent_to_the_pane(fleet) == [
            ["pane", "send-text", "w1:p9", "ping"],
            ["pane", "send-keys", "w1:p9", "Enter"],
        ]

    def test_refuses_to_swallow_input_when_no_pane_hosts_the_agent(self, monkeypatch):
        FakeHerdrFleet().with_agent_pane("clawde", "steward", "w1:p9").install_into(
            monkeypatch
        )
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        with pytest.raises(RuntimeError, match="jenny"):
            backend.send_input_text("ping")


class TestCancelGracefully:
    def test_interrupts_the_agent_pane(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.cancel_gracefully()
        assert commands_sent_to_the_pane(fleet) == [
            ["pane", "send-keys", "w1:p9", "C-c"]
        ]

    def test_stays_quiet_when_no_pane_hosts_the_agent(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "steward", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.cancel_gracefully()
        assert commands_sent_to_the_pane(fleet) == []


class TestStop:
    def test_never_closes_the_pane_it_only_attached_to(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        fleet.invocations.clear()
        backend.stop()
        assert fleet.invocations == []

    def test_reattaches_from_scratch_after_stopping(self, monkeypatch):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.showing("⏺ said before the peer restarted\n")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        backend.stop()
        fleet.invocations.clear()
        assert backend.observe().is_alive is True
        assert ["workspace", "list"] in fleet.invocations
