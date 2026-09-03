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

    def pane_is_idle(self, pane_handle, harness_runtime_profile):
        self.profiles_seen = getattr(self, "profiles_seen", []) + [
            harness_runtime_profile
        ]
        return pane_handle in self.idle_agent_names


def _wrapper(agent_name):
    return {
        "agent_name": agent_name,
        "tmux_session": "clawde",
        "config_file_path": f"/launch-config/{agent_name}.json",
    }


def test_select_wrappers_with_in_flight_work_skips_idle_agents(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "wW:p14")
    monkeypatch.setattr(
        clawde_redeploy,
        "load_harness_runtime_profile_from_launch_config",
        lambda config_file_path: f"profile-for:{config_file_path}",
    )
    backend = _FakePaneStateBackend(idle_agent_names={"silver"})
    wrappers = [_wrapper("silver"), _wrapper("steward")]
    result = clawde_redeploy.select_wrappers_with_in_flight_work_before_restart(
        wrappers, backend
    )
    assert result == [_wrapper("steward")]
    assert backend.profiles_seen == [
        "profile-for:/launch-config/silver.json",
        "profile-for:/launch-config/steward.json",
    ], "the idle check must read each agent's own harness runtime profile"
    assert os.environ.get("HERDR_PANE_ID") is None, (
        "the pre-restart pane read must scrub the invoking pane's HERDR_PANE_ID so the "
        "herdr backend resolves each agent's own tab by label instead of reading the "
        "pane that ran the rebuild"
    )


def test_select_wrappers_treats_unresolved_pane_as_in_flight():
    class _UnresolvedPaneBackend:
        def prepare_pane_handle(self, session_name, window_name):
            return None

        def pane_is_idle(self, pane_handle, harness_runtime_profile):
            raise AssertionError("must not probe idleness when the pane is unresolved")

    wrappers = [{"agent_name": "ghost", "tmux_session": "clawde"}]
    assert (
        clawde_redeploy.select_wrappers_with_in_flight_work_before_restart(
            wrappers, _UnresolvedPaneBackend()
        )
        == wrappers
    )


def test_a_wrapper_whose_launch_config_cannot_be_read_counts_as_in_flight(monkeypatch):
    def refuse(config_file_path):
        raise OSError(f"cannot read {config_file_path}")

    monkeypatch.setattr(
        clawde_redeploy, "load_harness_runtime_profile_from_launch_config", refuse
    )
    backend = _FakePaneStateBackend(idle_agent_names={"steward"})
    wrappers = [_wrapper("steward")]
    assert (
        clawde_redeploy.select_wrappers_with_in_flight_work_before_restart(
            wrappers, backend
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
