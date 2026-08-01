from a2a_server.fleet.agent_metadata import FleetAgentMetadata
from a2a_server.fleet.observation_loop import FleetObservationLoop
from a2a_server.fleet.registry import AttachedAgentRegistry

from fake_herdr_fleet import FakeHerdrFleet

DAEMON_BASE_URL = "http://127.0.0.1:7000"


def build_loop_over(metadata: dict | None = None) -> tuple:
    registry = AttachedAgentRegistry(
        FleetAgentMetadata(metadata or {}), DAEMON_BASE_URL
    )
    return registry, FleetObservationLoop(registry)


def attached_names(registry: AttachedAgentRegistry) -> list[str]:
    return sorted(session.peer_name for session in registry.every_session())


def test_every_agent_pane_is_attached_without_being_declared(monkeypatch):
    FakeHerdrFleet().with_agent_pane("p1", tab_label="jenny").with_agent_pane(
        "p2", tab_label="betha-qa"
    ).install_into(monkeypatch)
    registry, loop = build_loop_over()

    loop.run_one_pass()

    assert attached_names(registry) == ["betha-qa", "jenny"]


def test_a_declared_agent_takes_its_description_from_the_metadata(monkeypatch):
    FakeHerdrFleet().with_agent_pane("p1", tab_label="jenny").install_into(monkeypatch)
    registry, loop = build_loop_over(
        {"agents": {"jenny": {"description": "the router"}}}
    )

    loop.run_one_pass()

    assert registry.session_named("jenny").description == "the router"


def test_an_undeclared_agent_still_gets_a_card_describing_its_harness(monkeypatch):
    FakeHerdrFleet().with_agent_pane(
        "p1", tab_label="betha-qa", agent="opencode"
    ).install_into(monkeypatch)
    registry, loop = build_loop_over()

    loop.run_one_pass()

    assert registry.session_named("betha-qa").description == "opencode session betha-qa"


def test_a_closed_pane_is_dropped_from_the_registry(monkeypatch):
    fleet = (
        FakeHerdrFleet()
        .with_agent_pane("p1", tab_label="jenny")
        .with_agent_pane("p2", tab_label="betha-qa")
    )
    fleet.install_into(monkeypatch)
    registry, loop = build_loop_over()
    loop.run_one_pass()

    fleet.with_pane_removed("p2")
    loop.run_one_pass()

    assert attached_names(registry) == ["jenny"]


def test_a_respawned_agent_is_re_attached_to_its_new_pane(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane("p1", tab_label="jenny")
    fleet.install_into(monkeypatch)
    registry, loop = build_loop_over()
    loop.run_one_pass()

    fleet.with_pane_removed("p1")
    fleet.with_agent_pane("p2", tab_label="jenny")
    loop.run_one_pass()

    assert registry.session_named("jenny").pane_id == "p2"


def test_an_empty_pane_list_is_treated_as_herdr_being_unreachable(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane("p1", tab_label="jenny")
    fleet.install_into(monkeypatch)
    registry, loop = build_loop_over()
    loop.run_one_pass()

    fleet.panes = []
    loop.run_one_pass()

    assert attached_names(registry) == ["jenny"]


def test_the_loop_never_captures_a_pane_that_holds_no_task(monkeypatch):
    fleet = (
        FakeHerdrFleet()
        .with_agent_pane("p1", tab_label="jenny")
        .with_agent_pane("p2", tab_label="betha-qa")
    )
    fleet.install_into(monkeypatch)
    registry, loop = build_loop_over()
    loop.run_one_pass()
    captures_taken_while_attaching = len(fleet.invocations_matching(["pane", "read"]))

    loop.run_one_pass()
    loop.run_one_pass()

    assert (
        len(fleet.invocations_matching(["pane", "read"]))
        == captures_taken_while_attaching
    )
