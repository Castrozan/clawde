import datetime
import importlib.util
import pathlib
import sys

from heartbeat_test_support import load_heartbeat_module


def _load_cron_module():
    module_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat" / "cron.py"
    )
    module_spec = importlib.util.spec_from_file_location("heartbeat_cron", module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["heartbeat_cron"] = module
    module_spec.loader.exec_module(module)
    return module


cron_module = _load_cron_module()


def test_step_field_matches_every_fifteenth_minute():
    assert cron_module.cron_field_matches("*/15", 0, 0, 59)
    assert cron_module.cron_field_matches("*/15", 15, 0, 59)
    assert cron_module.cron_field_matches("*/15", 45, 0, 59)


def test_step_field_rejects_off_step_minute():
    assert not cron_module.cron_field_matches("*/15", 7, 0, 59)
    assert not cron_module.cron_field_matches("*/15", 14, 0, 59)


def test_comma_list_field_matches_only_listed_values():
    assert cron_module.cron_field_matches("3,33", 3, 0, 59)
    assert cron_module.cron_field_matches("3,33", 33, 0, 59)
    assert not cron_module.cron_field_matches("3,33", 4, 0, 59)
    assert not cron_module.cron_field_matches("3,33", 30, 0, 59)


def test_single_value_field_is_exact():
    assert cron_module.cron_field_matches("5", 5, 0, 59)
    assert not cron_module.cron_field_matches("5", 6, 0, 59)


def test_range_field_is_inclusive():
    assert cron_module.cron_field_matches("9-17", 9, 0, 23)
    assert cron_module.cron_field_matches("9-17", 17, 0, 23)
    assert not cron_module.cron_field_matches("9-17", 18, 0, 23)


def test_full_expression_matches_quarter_hour_any_day():
    at_quarter = datetime.datetime(2026, 6, 6, 14, 15, 0)
    off_quarter = datetime.datetime(2026, 6, 6, 14, 16, 0)
    assert cron_module.cron_expression_matches("*/15 * * * *", at_quarter)
    assert not cron_module.cron_expression_matches("*/15 * * * *", off_quarter)


def test_seconds_until_next_minute_never_exceeds_sixty():
    mid_minute = datetime.datetime(2026, 6, 6, 14, 15, 42, 500_000)
    seconds = cron_module.seconds_until_next_minute_boundary(mid_minute)
    assert 0 < seconds <= 60


driver = load_heartbeat_module("driver")

HEARTBEAT_PROMPT = "<heartbeat>"


class RecordingDeliveryObserver:
    def __init__(self):
        self.previous_delivery_judgments = 0
        self.pending_delivery_judgments = 0
        self.watched_deliveries = 0

    def judge_previous_delivery(self):
        self.previous_delivery_judgments += 1

    def judge_pending_delivery_without_baselining(self):
        self.pending_delivery_judgments += 1

    def watch_this_delivery_for_active_work(self, _backend, _pane_handle):
        self.watched_deliveries += 1


class FakeHeartbeatPane:
    def __init__(self, pane_is_idle):
        self.pane_is_idle_value = pane_is_idle
        self.sent_prompts = []

    def pane_is_idle(self, _pane_handle, _harness_runtime_profile):
        return self.pane_is_idle_value

    def send_prompt_to_pane(self, _pane_handle, prompt):
        self.sent_prompts.append(prompt)


def run_scheduled_tick(monkeypatch, gate_allows_wake, pane_is_idle_value):
    observer = RecordingDeliveryObserver()
    pane = FakeHeartbeatPane(pane_is_idle_value)
    monkeypatch.setattr(
        driver, "gate_allows_wake", lambda _gate_command: gate_allows_wake
    )
    driver.run_scheduled_heartbeat_tick(
        pane,
        "pane-handle",
        None,
        "gate-command",
        HEARTBEAT_PROMPT,
        observer,
    )
    return pane, observer


def test_a_gate_that_blocks_a_tick_still_judges_the_pending_delivery(monkeypatch):
    pane, observer = run_scheduled_tick(
        monkeypatch, gate_allows_wake=False, pane_is_idle_value=True
    )
    assert observer.pending_delivery_judgments == 1
    assert observer.previous_delivery_judgments == 0
    assert pane.sent_prompts == [], (
        "a blocked tick must never prompt the agent, only consume the refusal "
        "evidence the delivery it already sent left pending, so a gate that falls "
        "silent on an unchanged state still reaches the failover threshold"
    )


def test_an_allowed_tick_judges_the_previous_delivery_sends_and_watches(monkeypatch):
    pane, observer = run_scheduled_tick(
        monkeypatch, gate_allows_wake=True, pane_is_idle_value=True
    )
    assert observer.previous_delivery_judgments == 1
    assert pane.sent_prompts == [HEARTBEAT_PROMPT]
    assert observer.watched_deliveries == 1


def test_a_busy_pane_is_never_judged_or_prompted(monkeypatch):
    pane, observer = run_scheduled_tick(
        monkeypatch, gate_allows_wake=True, pane_is_idle_value=False
    )
    assert pane.sent_prompts == []
    assert observer.previous_delivery_judgments == 0
    assert observer.pending_delivery_judgments == 0
    assert observer.watched_deliveries == 0
