import importlib.util
import pathlib
import sys

AGENT_WRAPPER_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper"
)
sys.path.insert(0, str(AGENT_WRAPPER_DIRECTORY))


def _load_redeploy_signals_module():
    module_spec = importlib.util.spec_from_file_location(
        "redeploy_signals", AGENT_WRAPPER_DIRECTORY / "redeploy_signals.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


redeploy_signals = _load_redeploy_signals_module()


def test_restart_request_without_a_child_does_not_raise():
    redeploy_signals.redeploy_signal_state.current_child_process_id = None
    redeploy_signals.request_restart_now()


def test_restart_request_terminates_the_live_child_so_the_loop_relaunches(monkeypatch):
    terminated_process_ids = []
    monkeypatch.setattr(
        redeploy_signals, "terminate_process_tree", terminated_process_ids.append
    )
    redeploy_signals.redeploy_signal_state.current_child_process_id = 4242
    redeploy_signals.request_restart_now()
    assert terminated_process_ids == [4242], (
        "a redeploy signal only needs to kill the running child; the supervisor loop "
        "then relaunches and resumes the persisted session on its own"
    )


def test_register_current_child_process_id_updates_state():
    redeploy_signals.register_current_child_process_id(4242)
    assert redeploy_signals.redeploy_signal_state.current_child_process_id == 4242
    redeploy_signals.register_current_child_process_id(None)
    assert redeploy_signals.redeploy_signal_state.current_child_process_id is None
