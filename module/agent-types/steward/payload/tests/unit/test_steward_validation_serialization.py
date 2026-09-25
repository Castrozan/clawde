import os
import signal
import subprocess
import sys
import time

import pytest

from steward_test_helpers import steward_defer_to_rebuild


def wait_for_file(path):
    deadline = time.monotonic() + 5
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert path.exists()


def validation_command(tmp_path, program):
    return [
        sys.executable,
        steward_defer_to_rebuild.__file__,
        "--rebuild-lock-directory",
        str(tmp_path / "operator-rebuild.lock.d"),
        "--poll-interval-seconds",
        "0.01",
        "--",
        sys.executable,
        "-c",
        program,
    ]


def test_validation_workers_do_not_overlap(tmp_path):
    first_started = tmp_path / "first-started"
    release_first = tmp_path / "release-first"
    second_started = tmp_path / "second-started"
    first_program = (
        "import pathlib, time; "
        f"pathlib.Path({str(first_started)!r}).touch(); "
        f"release = pathlib.Path({str(release_first)!r}); "
        "exec('while not release.exists(): time.sleep(0.01)')"
    )
    second_program = f"import pathlib; pathlib.Path({str(second_started)!r}).touch()"
    first = subprocess.Popen(validation_command(tmp_path, first_program))
    second = None
    try:
        wait_for_file(first_started)
        second = subprocess.Popen(validation_command(tmp_path, second_program))
        with pytest.raises(subprocess.TimeoutExpired):
            second.wait(timeout=0.5)
        assert not second_started.exists()
        release_first.touch()
        assert first.wait(timeout=5) == 0
        assert second.wait(timeout=5) == 0
        assert second_started.exists()
    finally:
        release_first.touch()
        first.wait(timeout=5)
        if second is not None:
            second.wait(timeout=5)


def test_worker_keeps_validation_lock_if_guard_dies(tmp_path):
    started = tmp_path / "started"
    release = tmp_path / "release"
    program = (
        "import os, pathlib, time; "
        f"pathlib.Path({str(started)!r}).write_text(str(os.getpid())); "
        f"release = pathlib.Path({str(release)!r}); "
        "exec('while not release.exists(): time.sleep(0.01)')"
    )
    guard = subprocess.Popen(validation_command(tmp_path, program))
    successor = None
    try:
        wait_for_file(started)
        guard.kill()
        guard.wait(timeout=5)
        successor = subprocess.Popen(validation_command(tmp_path, "pass"))
        with pytest.raises(subprocess.TimeoutExpired):
            successor.wait(timeout=0.5)
        release.touch()
        assert successor.wait(timeout=5) == 0
    finally:
        release.touch()
        if guard.poll() is None:
            guard.wait(timeout=5)
        if started.exists():
            try:
                os.kill(int(started.read_text()), signal.SIGTERM)
            except ProcessLookupError:
                pass
        if successor is not None:
            successor.wait(timeout=5)


def test_darwin_validation_uses_background_io_policy(monkeypatch):
    monkeypatch.setattr(steward_defer_to_rebuild.sys, "platform", "darwin")
    monkeypatch.setattr(
        steward_defer_to_rebuild.shutil,
        "which",
        lambda command: "/usr/sbin/taskpolicy" if command == "taskpolicy" else None,
    )

    assert steward_defer_to_rebuild.low_io_priority_command(["validator"]) == [
        "/usr/sbin/taskpolicy",
        "-b",
        "validator",
    ]


def test_failed_validation_releases_lock_and_preserves_exit_code(tmp_path):
    failed = subprocess.run(
        validation_command(tmp_path, "raise SystemExit(42)"), timeout=5
    )
    successor = subprocess.run(validation_command(tmp_path, "pass"), timeout=5)

    assert failed.returncode == 42
    assert successor.returncode == 0
