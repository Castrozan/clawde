import importlib.util
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def _load_change_gate_module():
    sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / "change_gate.py"
    module_spec = importlib.util.spec_from_file_location("change_gate", module_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


change_gate = _load_change_gate_module()


def stub_probe(monkeypatch, return_code, fingerprint):
    monkeypatch.setattr(
        change_gate, "run_probe", lambda probe_command: (return_code, fingerprint)
    )


def test_actionable_fingerprint_fires_once_then_suppresses(monkeypatch, tmp_path):
    state_file = tmp_path / "steward"
    stub_probe(monkeypatch, 0, "diverged-behind-1")
    assert change_gate.gate_fires("probe", state_file) is True
    assert change_gate.gate_fires("probe", state_file) is False
    assert change_gate.gate_fires("probe", state_file) is False


def test_changed_fingerprint_fires_again(monkeypatch, tmp_path):
    state_file = tmp_path / "steward"
    stub_probe(monkeypatch, 0, "diverged-behind-1")
    assert change_gate.gate_fires("probe", state_file) is True
    stub_probe(monkeypatch, 0, "diverged-behind-2")
    assert change_gate.gate_fires("probe", state_file) is True


def test_empty_probe_output_skips_and_forgets(monkeypatch, tmp_path):
    state_file = tmp_path / "steward"
    stub_probe(monkeypatch, 0, "diverged-behind-1")
    assert change_gate.gate_fires("probe", state_file) is True
    stub_probe(monkeypatch, 0, "")
    assert change_gate.gate_fires("probe", state_file) is False
    assert not state_file.exists()
    stub_probe(monkeypatch, 0, "diverged-behind-1")
    assert change_gate.gate_fires("probe", state_file) is True


def test_failed_probe_skips_and_forgets(monkeypatch, tmp_path):
    state_file = tmp_path / "steward"
    stub_probe(monkeypatch, 0, "diverged-behind-1")
    assert change_gate.gate_fires("probe", state_file) is True
    stub_probe(monkeypatch, 3, "")
    assert change_gate.gate_fires("probe", state_file) is False
    assert not state_file.exists()


def test_default_state_file_namespaces_by_label(monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", "/state")
    assert change_gate.default_state_file("alpha-pm") == pathlib.Path(
        "/state/clawde-heartbeat-change-gate/alpha-pm"
    )


def test_runs_real_probe_command_and_exits_on_change(monkeypatch, tmp_path):
    state_file = tmp_path / "pm"
    assert change_gate.gate_fires("printf actionable", state_file) is True
    assert change_gate.gate_fires("printf actionable", state_file) is False
    assert change_gate.gate_fires("true", state_file) is False


def test_a_retry_budget_refires_an_unchanged_state_then_falls_silent(tmp_path):
    state_file = tmp_path / "steward"
    fires = [
        change_gate.gate_fires("echo pending", state_file, retries_while_pending=2)
        for _tick in range(5)
    ]

    assert fires == [True, True, True, False, False]


def test_a_changed_state_resets_the_retry_budget(tmp_path):
    state_file = tmp_path / "steward"
    change_gate.gate_fires("echo pending", state_file, retries_while_pending=1)
    change_gate.gate_fires("echo pending", state_file, retries_while_pending=1)

    assert (
        change_gate.gate_fires("echo pending", state_file, retries_while_pending=1)
        is False
    )
    assert (
        change_gate.gate_fires("echo moved", state_file, retries_while_pending=1)
        is True
    )
    assert (
        change_gate.gate_fires("echo moved", state_file, retries_while_pending=1)
        is True
    )


def test_the_default_budget_keeps_the_gate_purely_edge_triggered(tmp_path):
    state_file = tmp_path / "steward"

    assert change_gate.gate_fires("echo pending", state_file) is True
    assert change_gate.gate_fires("echo pending", state_file) is False


def test_a_clean_probe_forgets_the_retry_budget(tmp_path):
    state_file = tmp_path / "steward"
    change_gate.gate_fires("echo pending", state_file, retries_while_pending=2)

    assert change_gate.gate_fires("true", state_file, retries_while_pending=2) is False
    assert not state_file.exists()
    assert (
        change_gate.gate_fires("echo pending", state_file, retries_while_pending=2)
        is True
    )


def test_a_legacy_plain_text_state_file_is_read_as_one_prior_fire(tmp_path):
    state_file = tmp_path / "steward"
    state_file.write_text("pending")

    assert (
        change_gate.gate_fires("echo pending", state_file, retries_while_pending=1)
        is True
    )
    assert (
        change_gate.gate_fires("echo pending", state_file, retries_while_pending=1)
        is False
    )
