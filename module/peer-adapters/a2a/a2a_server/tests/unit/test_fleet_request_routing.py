import json

from a2a_server.fleet.agent_metadata import FleetAgentMetadata
from a2a_server.fleet.http_handler import route_get_request, route_post_request
from a2a_server.fleet.observation_loop import FleetObservationLoop
from a2a_server.fleet.registry import AttachedAgentRegistry
from a2a_server.fleet.request_router import FleetRequestRouter

from fake_herdr_fleet import FakeHerdrFleet

DAEMON_BASE_URL = "http://127.0.0.1:7000"


def build_router_over_a_two_agent_fleet(monkeypatch) -> FleetRequestRouter:
    monkeypatch.setattr("a2a_server.backends.herdr_backend.time.sleep", lambda _: None)
    FakeHerdrFleet().with_agent_pane("p1", tab_label="jenny").with_agent_pane(
        "p2", tab_label="betha-qa"
    ).install_into(monkeypatch)
    registry = AttachedAgentRegistry(FleetAgentMetadata({}), DAEMON_BASE_URL)
    FleetObservationLoop(registry).run_one_pass()
    return FleetRequestRouter(registry)


def decoded(response: tuple[int, str, bytes]) -> tuple[int, dict]:
    status_code, _, body_bytes = response
    return status_code, json.loads(body_bytes.decode("utf-8"))


def test_the_directory_lists_every_attached_agent(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)

    status_code, document = decoded(route_get_request(router, "/agents")())

    assert status_code == 200
    assert [entry["name"] for entry in document["agents"]] == ["betha-qa", "jenny"]


def test_each_agent_card_is_addressed_under_its_own_path(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)

    status_code, card = decoded(
        route_get_request(router, "/agents/jenny/.well-known/agent.json")()
    )

    assert status_code == 200
    assert card["name"] == "jenny"
    assert card["url"] == f"{DAEMON_BASE_URL}/agents/jenny"


def test_an_unknown_agent_names_the_ones_that_are_attached(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)

    status_code, document = decoded(
        route_post_request(router, "/agents/nobody/tasks/send", b'{"input": "hello"}')()
    )

    assert status_code == 404
    assert document["error"] == "unknown_agent"
    assert document["attached"] == ["betha-qa", "jenny"]


def test_a_task_is_accepted_and_readable_back_under_the_same_agent(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)

    submit_status, submitted = decoded(
        route_post_request(router, "/agents/jenny/tasks/send", b'{"input": "hi"}')()
    )
    read_status, read_back = decoded(
        route_get_request(router, f"/agents/jenny/tasks/{submitted['id']}")()
    )

    assert submit_status == 201
    assert read_status == 200
    assert read_back["id"] == submitted["id"]


def test_a_task_on_one_agent_is_invisible_to_another(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)
    _, submitted = decoded(
        route_post_request(router, "/agents/jenny/tasks/send", b'{"input": "hi"}')()
    )

    status_code, _ = decoded(
        route_get_request(router, f"/agents/betha-qa/tasks/{submitted['id']}")()
    )

    assert status_code == 404


def test_a_busy_agent_refuses_a_second_task_while_its_neighbour_accepts_one(
    monkeypatch,
):
    router = build_router_over_a_two_agent_fleet(monkeypatch)
    route_post_request(router, "/agents/jenny/tasks/send", b'{"input": "first"}')()

    busy_status, _ = decoded(
        route_post_request(router, "/agents/jenny/tasks/send", b'{"input": "second"}')()
    )
    neighbour_status, _ = decoded(
        route_post_request(router, "/agents/betha-qa/tasks/send", b'{"input": "hi"}')()
    )

    assert busy_status == 409
    assert neighbour_status == 201


def test_the_health_probe_answers_without_naming_an_agent(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)

    status_code, document = decoded(route_get_request(router, "/health")())

    assert status_code == 200
    assert document == {"status": "ok"}


def test_an_unrouteable_path_is_a_not_found_rather_than_a_crash(monkeypatch):
    router = build_router_over_a_two_agent_fleet(monkeypatch)

    assert decoded(route_get_request(router, "/agents/")())[0] == 200
    assert decoded(route_get_request(router, "/nonsense")())[0] == 404
    assert decoded(route_post_request(router, "/nonsense", b"{}")())[0] == 404
