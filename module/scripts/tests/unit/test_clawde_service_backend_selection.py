import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from herdr_backend_test_support import base, herdr_backend


def test_select_supervisor_backend_dispatches_on_environment(monkeypatch):
    monkeypatch.setenv(base.MULTIPLEXER_ENVIRONMENT_VARIABLE, "herdr")
    assert isinstance(
        base.select_supervisor_backend(), herdr_backend.HerdrSupervisorBackend
    )
    monkeypatch.delenv(base.MULTIPLEXER_ENVIRONMENT_VARIABLE, raising=False)
    assert not isinstance(
        base.select_supervisor_backend(), herdr_backend.HerdrSupervisorBackend
    )
