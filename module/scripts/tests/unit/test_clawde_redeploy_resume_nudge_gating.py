import importlib.util
import os
import pathlib

CLAWDE_SCRIPTS_DIRECTORY = pathlib.Path(__file__).resolve().parent.parent.parent


def _load_clawde_redeploy_module():
    module_spec = importlib.util.spec_from_file_location(
        "clawde_redeploy", CLAWDE_SCRIPTS_DIRECTORY / "clawde-redeploy.py"
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


clawde_redeploy = _load_clawde_redeploy_module()


class _FakePaneStateBackend:
    def __init__(self, idle_agent_names):
        self.idle_agent_names = idle_agent_names
        self.prepared_for = []

    def prepare_pane_handle(self, session_name, window_name):
        self.prepared_for.append((session_name, window_name))
        return window_name

    def pane_is_idle(self, pane_handle):
        return pane_handle in self.idle_agent_names


def test_select_wrappers_with_in_flight_work_skips_idle_agents(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "wW:p14")
    backend = _FakePaneStateBackend(idle_agent_names={"silver"})
    wrappers = [
        {"agent_name": "silver", "tmux_session": "clawde"},
        {"agent_name": "steward", "tmux_session": "clawde"},
    ]
    result = clawde_redeploy.select_wrappers_with_in_flight_work_before_restart(
        wrappers, backend
    )
    assert result == [{"agent_name": "steward", "tmux_session": "clawde"}]
    assert os.environ.get("HERDR_PANE_ID") is None, (
        "the pre-restart pane read must scrub the invoking pane's HERDR_PANE_ID so the "
        "herdr backend resolves each agent's own tab by label instead of reading the "
        "pane that ran the rebuild"
    )


def test_select_wrappers_treats_unresolved_pane_as_in_flight():
    class _UnresolvedPaneBackend:
        def prepare_pane_handle(self, session_name, window_name):
            return None

        def pane_is_idle(self, pane_handle):
            raise AssertionError("must not probe idleness when the pane is unresolved")

    wrappers = [{"agent_name": "ghost", "tmux_session": "clawde"}]
    assert (
        clawde_redeploy.select_wrappers_with_in_flight_work_before_restart(
            wrappers, _UnresolvedPaneBackend()
        )
        == wrappers
    )


def test_load_heartbeat_backend_returns_none_without_env(monkeypatch):
    monkeypatch.delenv(
        clawde_redeploy.HEARTBEAT_SCRIPTS_DIRECTORY_ENVIRONMENT_VARIABLE, raising=False
    )
    assert (
        clawde_redeploy.load_heartbeat_backend_or_none_when_pane_state_is_unavailable()
        is None
    )
