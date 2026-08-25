import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "clawde-service")
)

import sidecar_process_reconcile
from sidecar_process_test_support import (
    SIDECAR_NAME,
    make_sidecar_specification,
    record_process_lookups,
    record_the_sidecar_as_launched_from_its_current_command,
)


def reconcile_a_running_sidecar(specification, monkeypatch, live_process_ids=(4321,)):
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, list(live_process_ids)
    )
    sidecar_process_reconcile.reconcile_one_sidecar_process(specification, True)
    return spawned_specifications, terminated_process_ids


def test_a_sidecar_still_running_superseded_code_is_replaced(tmp_path, monkeypatch):
    specification = record_the_sidecar_as_launched_from_its_current_command(
        make_sidecar_specification(tmp_path, command="python3 /nix/store/old-bridge.py")
    )
    specification["command"] = "python3 /nix/store/new-bridge.py"

    spawned_specifications, terminated_process_ids = reconcile_a_running_sidecar(
        specification, monkeypatch
    )

    assert terminated_process_ids == [4321]
    assert [specification["name"] for specification in spawned_specifications] == [
        SIDECAR_NAME
    ]


def test_every_process_of_a_superseded_sidecar_is_terminated_before_the_replacement(
    tmp_path, monkeypatch
):
    waited_for_process_ids = []
    specification = record_the_sidecar_as_launched_from_its_current_command(
        make_sidecar_specification(tmp_path, command="python3 /nix/store/old-bridge.py")
    )
    specification["command"] = "python3 /nix/store/new-bridge.py"
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [700, 120, 450]
    )
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "wait_for_process_to_exit",
        waited_for_process_ids.append,
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(specification, True)

    assert terminated_process_ids == [120, 450, 700]
    assert waited_for_process_ids == [120, 450, 700]
    assert len(spawned_specifications) == 1


def test_a_sidecar_running_the_current_code_is_left_alone(tmp_path, monkeypatch):
    specification = record_the_sidecar_as_launched_from_its_current_command(
        make_sidecar_specification(tmp_path, command="python3 /nix/store/bridge.py")
    )

    spawned_specifications, terminated_process_ids = reconcile_a_running_sidecar(
        specification, monkeypatch
    )

    assert spawned_specifications == []
    assert terminated_process_ids == []


def test_a_sidecar_launched_before_this_record_existed_is_replaced_exactly_once(
    tmp_path, monkeypatch
):
    specification = make_sidecar_specification(tmp_path, command="true")

    _, first_terminated_process_ids = reconcile_a_running_sidecar(
        specification, monkeypatch
    )
    sidecar_process_reconcile.record_spawned_command(specification)
    _, second_terminated_process_ids = reconcile_a_running_sidecar(
        specification, monkeypatch
    )

    assert first_terminated_process_ids == [4321]
    assert second_terminated_process_ids == []


def test_spawning_records_the_command_it_launched(tmp_path):
    specification = make_sidecar_specification(tmp_path, command="true")

    sidecar_process_reconcile.spawn_sidecar_process(specification)

    assert sidecar_process_reconcile.recorded_spawned_command(specification) == "true"


def test_a_superseded_sidecar_that_should_stop_is_terminated_without_replacement(
    tmp_path, monkeypatch
):
    specification = record_the_sidecar_as_launched_from_its_current_command(
        make_sidecar_specification(tmp_path, command="python3 /nix/store/old-bridge.py")
    )
    specification["command"] = "python3 /nix/store/new-bridge.py"
    spawned_specifications, terminated_process_ids = record_process_lookups(
        monkeypatch, [4321]
    )

    sidecar_process_reconcile.reconcile_one_sidecar_process(specification, False)

    assert terminated_process_ids == [4321]
    assert spawned_specifications == []


def test_waiting_returns_as_soon_as_the_process_is_gone(monkeypatch):
    monkeypatch.setattr(
        sidecar_process_reconcile, "process_is_alive", lambda _process_id: False
    )
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "time",
        type("NeverSleeps", (), {"sleep": staticmethod(lambda _seconds: None)}),
    )

    sidecar_process_reconcile.wait_for_process_to_exit(4321)


def test_waiting_gives_up_on_a_process_that_refuses_to_exit(monkeypatch):
    slept_seconds = []
    monkeypatch.setattr(
        sidecar_process_reconcile, "process_is_alive", lambda _process_id: True
    )
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "time",
        type("CountsSleeps", (), {"sleep": staticmethod(slept_seconds.append)}),
    )

    sidecar_process_reconcile.wait_for_process_to_exit(4321)

    assert len(slept_seconds) == sidecar_process_reconcile.termination_poll_attempts()
