import subprocess
from pathlib import Path

import pytest

from steward_test_helpers import steward_defer_to_rebuild


class ValidationProcess:
    def __init__(self, process_id, wait_results):
        self.pid = process_id
        self.wait_results = iter(wait_results)

    def wait(self, timeout=None):
        result = next(self.wait_results)
        if result == "timeout":
            raise subprocess.TimeoutExpired("validator", timeout)
        return result


class InterruptedValidationProcess:
    pid = 4312

    def wait(self, timeout=None):
        raise KeyboardInterrupt


def test_live_rebuild_owner_keeps_validation_waiting(monkeypatch, tmp_path):
    lock_directory = tmp_path / "rebuild.lock.d"
    lock_directory.mkdir()
    (lock_directory / "owner").write_text("pid=4312\n")
    process_states = iter([True, False])
    sleep_intervals = []
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "process_is_running",
        lambda process_id: next(process_states),
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild.time,
        "sleep",
        lambda seconds: sleep_intervals.append(seconds),
    )

    steward_defer_to_rebuild.wait_until_rebuild_finishes(lock_directory, 3)

    assert sleep_intervals == [3]


def test_stale_rebuild_owner_does_not_delay_validation(monkeypatch, tmp_path):
    lock_directory = tmp_path / "rebuild.lock.d"
    lock_directory.mkdir()
    (lock_directory / "owner").write_text("pid=4312\n")
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "process_is_running",
        lambda process_id: False,
    )

    assert steward_defer_to_rebuild.rebuild_is_running(lock_directory) is False


def test_incomplete_rebuild_lock_is_treated_as_active(tmp_path):
    lock_directory = tmp_path / "rebuild.lock.d"
    lock_directory.mkdir()

    assert steward_defer_to_rebuild.rebuild_is_running(lock_directory) is True


def test_validation_command_runs_at_low_cpu_priority(monkeypatch):
    nice_adjustments = []
    monkeypatch.setattr(steward_defer_to_rebuild.os, "nice", nice_adjustments.append)

    steward_defer_to_rebuild.lower_cpu_priority()

    assert nice_adjustments == [19]


def test_validation_command_runs_at_low_io_priority(monkeypatch):
    monkeypatch.setattr(
        steward_defer_to_rebuild.shutil,
        "which",
        lambda command: "/run/current-system/sw/bin/ionice",
    )

    command = steward_defer_to_rebuild.low_io_priority_command(
        ["validator", "--revision=abc"]
    )

    assert command == [
        "/run/current-system/sw/bin/ionice",
        "-c",
        "3",
        "validator",
        "--revision=abc",
    ]


def test_missing_ionice_runs_validation_command_directly(monkeypatch):
    monkeypatch.setattr(steward_defer_to_rebuild.shutil, "which", lambda command: None)

    command = steward_defer_to_rebuild.low_io_priority_command(["validator"])

    assert command == ["validator"]


def test_rebuild_starting_during_validation_preempts_and_restarts_it(monkeypatch):
    first_process = ValidationProcess(4312, ["timeout"])
    second_process = ValidationProcess(4313, [0])
    validation_processes = iter([first_process, second_process])
    rebuild_states = iter([False, True, False])
    terminated_processes = []
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "rebuild_is_running",
        lambda lock_directory: next(rebuild_states),
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "start_validation_process",
        lambda command: next(validation_processes),
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "terminate_validation_process",
        terminated_processes.append,
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "lower_cpu_priority",
        lambda: None,
    )

    exit_code = steward_defer_to_rebuild.run_validation_with_rebuild_preemption(
        ["validator"],
        Path("/tmp/rebuild.lock.d"),
        1,
    )

    assert exit_code == 0
    assert terminated_processes == [first_process]


def test_terminated_leader_with_surviving_group_is_force_killed(monkeypatch):
    validation_process = ValidationProcess(4312, [0, 0])
    delivered_signals = []
    monkeypatch.setattr(
        steward_defer_to_rebuild.os,
        "killpg",
        lambda process_group_id, delivered_signal: delivered_signals.append(
            (process_group_id, delivered_signal)
        ),
    )

    steward_defer_to_rebuild.terminate_validation_process(validation_process)

    assert delivered_signals == [
        (4312, steward_defer_to_rebuild.signal.SIGTERM),
        (4312, steward_defer_to_rebuild.signal.SIGKILL),
    ]


def test_interrupted_guard_terminates_validation_process(monkeypatch):
    validation_process = InterruptedValidationProcess()
    terminated_processes = []
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "rebuild_is_running",
        lambda lock_directory: False,
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "start_validation_process",
        lambda command: validation_process,
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "terminate_validation_process",
        terminated_processes.append,
    )
    monkeypatch.setattr(
        steward_defer_to_rebuild,
        "lower_cpu_priority",
        lambda: None,
    )

    with pytest.raises(KeyboardInterrupt):
        steward_defer_to_rebuild.run_validation_with_rebuild_preemption(
            ["validator"],
            Path("/tmp/rebuild.lock.d"),
            1,
        )

    assert terminated_processes == [validation_process]
