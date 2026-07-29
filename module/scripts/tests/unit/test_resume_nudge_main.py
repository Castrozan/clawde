import os

import pytest
from harness_profile_test_helpers import CLAUDE_PROFILE_MAPPING, CODEX_PROFILE_MAPPING
from resume_nudge_test_support import (
    FakeHeartbeatBackend,
    load_resume_nudge_module,
    resume_nudge_argv,
    write_launch_config,
)

resume_nudge = load_resume_nudge_module()


@pytest.fixture
def claude_launch_config(tmp_path):
    return write_launch_config(tmp_path, CLAUDE_PROFILE_MAPPING)


def _run_main_with(monkeypatch, window_name, launch_config, repl_is_live=True):
    monkeypatch.setattr(
        resume_nudge.sys, "argv", resume_nudge_argv(window_name, launch_config)
    )
    monkeypatch.setattr(
        resume_nudge,
        "wait_for_live_harness_repl",
        lambda agent_name, fragment: repl_is_live,
    )
    fake_backend = FakeHeartbeatBackend()
    monkeypatch.setattr(resume_nudge, "select_heartbeat_backend", lambda: fake_backend)
    resume_nudge.main()
    return fake_backend


def test_main_skips_injection_when_agent_dormant(monkeypatch, claude_launch_config):
    fake_backend = _run_main_with(
        monkeypatch, "alpha-pm", claude_launch_config, repl_is_live=False
    )
    assert fake_backend.prompts_sent == []


def test_main_injects_when_agent_has_a_live_repl(monkeypatch, claude_launch_config):
    fake_backend = _run_main_with(monkeypatch, "bronze", claude_launch_config)
    assert fake_backend.prepared_for == ("clawde", "bronze")
    assert fake_backend.prompts_sent == [resume_nudge.RESUME_NUDGE_PROMPT]


def test_main_dismisses_pre_prompt_modal_before_injecting(
    monkeypatch, claude_launch_config
):
    fake_backend = _run_main_with(monkeypatch, "steward", claude_launch_config)
    assert fake_backend.dismiss_calls == 1, (
        "a warm redeploy must answer any pre-prompt dialog before injecting "
        "so the agent reaches its REPL instead of wedging at the dialog"
    )
    assert fake_backend.prompts_sent == [resume_nudge.RESUME_NUDGE_PROMPT]


def test_main_discards_inherited_pane_id_so_target_resolves_by_agent_label(
    monkeypatch, claude_launch_config
):
    monkeypatch.setenv("HERDR_PANE_ID", "wW:p14")
    observed_ambient_pane_id_at_prepare = {}

    class _AmbientPaneRecordingBackend(FakeHeartbeatBackend):
        def prepare_pane_handle(self, session_name, window_name):
            observed_ambient_pane_id_at_prepare["value"] = os.environ.get(
                "HERDR_PANE_ID"
            )
            return super().prepare_pane_handle(session_name, window_name)

    monkeypatch.setattr(
        resume_nudge.sys, "argv", resume_nudge_argv("bronze", claude_launch_config)
    )
    monkeypatch.setattr(
        resume_nudge, "wait_for_live_harness_repl", lambda agent_name, fragment: True
    )
    fake_backend = _AmbientPaneRecordingBackend()
    monkeypatch.setattr(resume_nudge, "select_heartbeat_backend", lambda: fake_backend)
    resume_nudge.main()

    assert observed_ambient_pane_id_at_prepare["value"] is None, (
        "clawde-redeploy fans out one resume nudge per agent as a detached subprocess "
        "that inherits the invoking pane's HERDR_PANE_ID; the nudge must scrub it so "
        "the herdr backend resolves each agent's own tab by its --window label instead "
        "of firing every agent's resume prompt into the pane that ran the rebuild"
    )
    assert fake_backend.prepared_for == ("clawde", "bronze")


def test_main_looks_for_the_harness_named_in_the_launch_config(monkeypatch, tmp_path):
    codex_launch_config = write_launch_config(tmp_path, CODEX_PROFILE_MAPPING)
    monkeypatch.setattr(
        resume_nudge.sys, "argv", resume_nudge_argv("steward", codex_launch_config)
    )
    process_fragments_looked_for = []

    def _record_fragment(agent_name, fragment):
        process_fragments_looked_for.append(fragment)
        return True

    monkeypatch.setattr(resume_nudge, "wait_for_live_harness_repl", _record_fragment)
    monkeypatch.setattr(
        resume_nudge, "select_heartbeat_backend", lambda: FakeHeartbeatBackend()
    )
    resume_nudge.main()
    assert process_fragments_looked_for == ["codex"], (
        "the resume nudge must look for the harness the agent actually runs, "
        "otherwise a codex agent reads as dormant and never gets nudged"
    )
