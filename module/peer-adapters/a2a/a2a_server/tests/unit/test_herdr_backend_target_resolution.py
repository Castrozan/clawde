from a2a_server.backends.herdr_backend import HerdrAttachedAgentBackend
from fake_herdr_fleet import FakeHerdrFleet


class TestResolvingTheAgentPane:
    def test_finds_the_pane_through_the_workspace_label_then_the_tab_label(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        assert backend.observe().is_alive is True
        assert ["workspace", "list"] in fleet.invocations
        assert ["tab", "list", "--workspace", "ws-of-clawde"] in fleet.invocations

    def test_reports_the_target_dead_when_the_workspace_label_matches_nothing(
        self, monkeypatch
    ):
        FakeHerdrFleet().with_agent_pane("other-fleet", "jenny", "w1:p9").install_into(
            monkeypatch
        )
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        assert backend.observe().is_alive is False

    def test_reports_the_target_dead_when_no_tab_carries_the_agent_name(
        self, monkeypatch
    ):
        FakeHerdrFleet().with_agent_pane("clawde", "steward", "w1:p9").install_into(
            monkeypatch
        )
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        assert backend.observe().is_alive is False

    def test_follows_the_agent_to_a_new_pane_after_the_tab_is_respawned(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        fleet.with_agent_pane("clawde", "jenny", "w1:p42")
        observation = backend.observe()
        assert observation.is_alive is True
        assert ["pane", "get", "w1:p42"] in fleet.invocations

    def test_stops_asking_the_multiplexer_to_resolve_a_pane_it_already_holds(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        fleet.invocations.clear()
        backend.observe()
        assert ["workspace", "list"] not in fleet.invocations

    def test_adopts_what_the_newly_resolved_pane_already_shows_as_the_baseline(
        self, monkeypatch
    ):
        fleet = FakeHerdrFleet().with_agent_pane("clawde", "jenny", "w1:p9")
        fleet.showing("scrollback line one\nscrollback line two\n")
        fleet.install_into(monkeypatch)
        backend = HerdrAttachedAgentBackend("clawde", "jenny")
        backend.start()
        assert backend.observe().raw_output_since_last_call == ""
