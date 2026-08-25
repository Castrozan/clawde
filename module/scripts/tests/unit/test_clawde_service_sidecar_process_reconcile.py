import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service")
)

import sidecar_process_reconcile
from sidecar_process_test_support import (
    AGENT_NAME,
    SIDECAR_NAME,
    make_sidecar_specification,
    make_sidecar_specification_with_lifetime,
    make_session_specification,
    record_process_lookups,
    record_the_sidecar_as_launched_from_its_current_command,
)


def test_a_sidecar_with_no_live_process_is_spawned(tmp_path, monkeypatch):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        make_sidecar_specification(tmp_path), True
    )

    assert [specification["name"] for specification in spawned_specifications] == [
        SIDECAR_NAME
    ]


def test_a_live_sidecar_is_never_relaunched(tmp_path, monkeypatch):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [4321]
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        record_the_sidecar_as_launched_from_its_current_command(
            make_sidecar_specification(tmp_path)
        ),
        True,
    )

    assert spawned_specifications == []
    assert terminated_process_ids == []


def test_duplicate_sidecar_processes_are_culled_down_to_the_oldest(
    tmp_path, monkeypatch
):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [700, 120, 450]
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        record_the_sidecar_as_launched_from_its_current_command(
            make_sidecar_specification(tmp_path)
        ),
        True,
    )

    assert terminated_process_ids == [450, 700]
    assert spawned_specifications == []


def test_a_sidecar_stops_once_its_agent_should_no_longer_run(tmp_path, monkeypatch):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [4321]
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        make_sidecar_specification(tmp_path), False
    )

    assert terminated_process_ids == [4321]
    assert spawned_specifications == []


def test_a_stopped_agents_sidecar_is_never_started(tmp_path, monkeypatch):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        make_sidecar_specification(tmp_path), False
    )

    assert spawned_specifications == []


def test_an_agent_declaring_no_sidecars_reconciles_without_spawning_anything(
    monkeypatch,
):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])

    sidecar_process_reconcile.reconcile_sidecar_processes_for_session(
        {"name": "clawde", "agents": [{"name": AGENT_NAME, "wrapper_command": "true"}]},
        {AGENT_NAME},
    )

    assert spawned_specifications == []


def test_a_sessions_sidecars_follow_their_own_agents_run_decision(
    tmp_path, monkeypatch
):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])

    sidecar_process_reconcile.reconcile_sidecar_processes_for_session(
        make_session_specification(tmp_path), set()
    )

    assert spawned_specifications == []

    spawned_specifications.clear()
    sidecar_process_reconcile.reconcile_sidecar_processes_for_session(
        make_session_specification(tmp_path), {AGENT_NAME}
    )

    assert [specification["name"] for specification in spawned_specifications] == [
        SIDECAR_NAME
    ]


def test_a_sidecar_disabled_by_its_transport_is_terminated_never_spawned(
    tmp_path, monkeypatch
):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [4321]
    )
    specification = make_sidecar_specification_with_lifetime(
        tmp_path, "agent", enabled=False
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        specification,
        sidecar_process_reconcile.sidecar_should_be_running_for(
            AGENT_NAME, specification, {AGENT_NAME}
        ),
    )

    assert terminated_process_ids == [4321]
    assert spawned_specifications == []


def test_a_sidecar_disabled_by_its_transport_never_spawns_even_for_a_running_agent(
    tmp_path, monkeypatch
):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])
    specification = make_sidecar_specification_with_lifetime(
        tmp_path, "agent", enabled=False
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        specification,
        sidecar_process_reconcile.sidecar_should_be_running_for(
            AGENT_NAME, specification, {AGENT_NAME}
        ),
    )

    assert spawned_specifications == []


def test_a_service_lifetime_sidecar_spawns_while_its_agent_is_dormant(
    tmp_path, monkeypatch
):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])
    specification = make_sidecar_specification_with_lifetime(tmp_path, "service")

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        specification,
        sidecar_process_reconcile.sidecar_should_be_running_for(
            AGENT_NAME, specification, set()
        ),
    )

    assert [specification["name"] for specification in spawned_specifications] == [
        SIDECAR_NAME
    ]


def test_a_service_lifetime_sidecar_survives_its_agents_dormancy(tmp_path, monkeypatch):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [4321]
    )
    specification = record_the_sidecar_as_launched_from_its_current_command(
        make_sidecar_specification_with_lifetime(tmp_path, "service")
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        specification,
        sidecar_process_reconcile.sidecar_should_be_running_for(
            AGENT_NAME, specification, set()
        ),
    )

    assert spawned_specifications == []
    assert terminated_process_ids == []


def test_an_agent_lifetime_sidecar_still_stops_with_its_dormant_agent(
    tmp_path, monkeypatch
):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [4321]
    )
    specification = make_sidecar_specification_with_lifetime(tmp_path, "agent")

    sidecar_process_reconcile.reconcile_one_sidecar_process(
        specification,
        sidecar_process_reconcile.sidecar_should_be_running_for(
            AGENT_NAME, specification, set()
        ),
    )

    assert terminated_process_ids == [4321]
    assert spawned_specifications == []


def test_a_service_lifetime_sidecar_stays_supervised_when_its_agent_should_not_run(
    tmp_path, monkeypatch
):
    spawned_specifications, _ = record_process_lookups(monkeypatch, [])

    session_specification = make_session_specification(tmp_path)
    session_specification["agents"][0]["sidecar_processes"][0]["lifetime"] = "service"

    sidecar_process_reconcile.reconcile_sidecar_processes_for_session(
        session_specification, set()
    )

    assert [specification["name"] for specification in spawned_specifications] == [
        SIDECAR_NAME
    ]
