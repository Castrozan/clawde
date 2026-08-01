from a2a_server.fleet import discovery
from a2a_server.fleet.naming import unique_peer_names_by_pane_id

from fake_herdr_fleet import FakeHerdrFleet


def discovered_names(fleet: FakeHerdrFleet) -> dict[str, str]:
    return unique_peer_names_by_pane_id(
        discovery.read_agent_panes_from_the_live_fleet(),
        discovery.read_tab_labels_by_tab_id(),
    )


def test_only_panes_herdr_flags_as_an_agent_become_peers(monkeypatch):
    FakeHerdrFleet().with_agent_pane("p1", tab_label="jenny").with_agent_pane(
        "p2", tab_label="a-plain-shell", agent=None
    ).install_into(monkeypatch)

    panes = discovery.read_agent_panes_from_the_live_fleet()

    assert [pane.pane_id for pane in panes] == ["p1"]


def test_an_undeclared_pane_is_named_after_its_herdr_tab(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane("p9", tab_label="betha-qa")
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {"p9": "betha-qa"}


def test_a_pane_with_no_tab_label_is_named_after_its_working_directory(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane(
        "p9", tab_label=None, cwd="/Users/lucas/repo/marketplace/"
    )
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {"p9": "marketplace"}


def test_a_pane_with_neither_label_nor_directory_falls_back_to_its_pane_id(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane("wS:p36", tab_label=None)
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {"wS:p36": "wS-p36"}


def test_colliding_names_are_disambiguated_so_every_peer_stays_addressable(monkeypatch):
    fleet = (
        FakeHerdrFleet()
        .with_agent_pane("wS:p1", tab_label=None, cwd="/repo/marketplace")
        .with_agent_pane("wS:p2", tab_label=None, cwd="/other/marketplace")
        .with_agent_pane("wS:p3", tab_label="jenny")
    )
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {
        "wS:p1": "marketplace-wS-p1",
        "wS:p2": "marketplace-wS-p2",
        "wS:p3": "jenny",
    }


def test_a_name_carrying_url_hostile_characters_is_sanitized(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane("p1", tab_label="feat/some thing")
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {"p1": "feat-some-thing"}


def test_discovery_reads_the_whole_fleet_with_one_call_per_collection(monkeypatch):
    fleet = (
        FakeHerdrFleet()
        .with_agent_pane("p1", tab_label="jenny")
        .with_agent_pane("p2", tab_label="steward")
    )
    fleet.install_into(monkeypatch)

    discovery.read_agent_panes_from_the_live_fleet()
    discovery.read_tab_labels_by_tab_id()

    assert len(fleet.invocations_matching(["pane", "list"])) == 1
    assert len(fleet.invocations_matching(["tab", "list"])) == 1


def test_a_tab_numbered_rather_than_named_falls_through_to_its_directory(monkeypatch):
    fleet = FakeHerdrFleet().with_agent_pane(
        "wS:p12", tab_label="3", cwd="/Users/lucas/repo/dotfiles"
    )
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {"wS:p12": "dotfiles"}


def test_two_numbered_tabs_in_one_repo_stay_distinct(monkeypatch):
    fleet = (
        FakeHerdrFleet()
        .with_agent_pane("wS:p1", tab_label="2", cwd="/repo/dotfiles")
        .with_agent_pane("wS:p2", tab_label="3", cwd="/repo/dotfiles")
    )
    fleet.install_into(monkeypatch)

    assert discovered_names(fleet) == {
        "wS:p1": "dotfiles-wS-p1",
        "wS:p2": "dotfiles-wS-p2",
    }
