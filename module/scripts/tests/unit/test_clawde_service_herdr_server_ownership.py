import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from herdr_backend_test_support import herdr_backend


def test_missing_herdr_server_is_reported_without_clawde_starting_one(
    monkeypatch, capsys
):
    def fail_if_clawde_starts_a_process(*_arguments, **_keyword_arguments):
        raise AssertionError("clawde must not own the herdr server process")

    monkeypatch.setattr(subprocess, "Popen", fail_if_clawde_starts_a_process)
    backend = herdr_backend.HerdrSupervisorBackend()
    monkeypatch.setattr(backend, "herdr_server_is_running", lambda: False)

    assert not backend.ensure_server_running()
    assert "herdr server must be managed independently" in capsys.readouterr().err
