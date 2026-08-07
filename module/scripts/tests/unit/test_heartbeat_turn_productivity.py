import importlib.util
import pathlib
import sys

from harness_profile_test_helpers import make_opencode_profile

OPENCODE_IDLE_PANE = (
    "  Build · DeepSeek V4 Flash (2x usage) OpenCode Go · high\n"
    "  /home/zanoni/clawde/steward          tab agents  ctrl+p commands\n"
)
OPENCODE_WORKING_PANE = (
    "  Build · DeepSeek V4 Flash (2x usage) OpenCode Go · high\n"
    "  /home/zanoni/clawde/steward   esc interrupt  ctrl+p commands\n"
)


def _load_heartbeat_turn_productivity_module():
    module_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent
        / "heartbeat"
        / "heartbeat_turn_productivity.py"
    )
    module_spec = importlib.util.spec_from_file_location(
        "heartbeat_turn_productivity", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["heartbeat_turn_productivity"] = module
    module_spec.loader.exec_module(module)
    return module


heartbeat_turn_productivity = _load_heartbeat_turn_productivity_module()


class PaneShowing:
    def __init__(self, pane_content):
        self.pane_content = pane_content
        self.observed_sleep_seconds = None

    def pane_is_idle(self, _pane_handle, harness_runtime_profile):
        return harness_runtime_profile.pane_is_at_idle_prompt(self.pane_content)

    def record_sleep(self, seconds):
        self.observed_sleep_seconds = seconds


def _turn_is_still_running(backend):
    return heartbeat_turn_productivity.delivered_turn_is_still_running(
        backend, "pane-handle", make_opencode_profile(), backend.record_sleep
    )


def test_a_turn_still_running_after_the_minimum_duration_counts_as_work():
    assert _turn_is_still_running(PaneShowing(OPENCODE_WORKING_PANE)) is True


def test_a_pane_back_at_its_prompt_after_the_minimum_duration_counts_as_no_work():
    assert _turn_is_still_running(PaneShowing(OPENCODE_IDLE_PANE)) is False, (
        "a provider refusing the request drops the agent back to its prompt within "
        "seconds; that is the only difference between a quota-parked agent and a "
        "working one, since both hold a live process and an idle-looking pane"
    )


def test_an_unreadable_pane_is_never_read_as_no_work():
    class PaneThatCannotBeCaptured(PaneShowing):
        def pane_is_idle(self, _pane_handle, _harness_runtime_profile):
            return False

    assert _turn_is_still_running(PaneThatCannotBeCaptured("")) is True, (
        "a failed capture must not accumulate toward a harness failover, because "
        "moving a healthy agent off its harness on multiplexer trouble is worse "
        "than missing one tick of evidence"
    )


def test_the_observation_waits_the_whole_minimum_productive_duration():
    backend = PaneShowing(OPENCODE_IDLE_PANE)
    _turn_is_still_running(backend)
    assert (
        backend.observed_sleep_seconds
        == heartbeat_turn_productivity.MINIMUM_PRODUCTIVE_TURN_SECONDS
    )
