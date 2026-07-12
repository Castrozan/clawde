import importlib.util
import os
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def _load_resume_nudge_module():
    sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / "resume_nudge.py"
    module_spec = importlib.util.spec_from_file_location("resume_nudge", module_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


resume_nudge = _load_resume_nudge_module()


class _CompletedProcessStub:
    def __init__(self, stdout):
        self.stdout = stdout


class _FakeBackend:
    def __init__(self):
        self.prepared_for = None
        self.dismiss_calls = 0
        self.prompts_sent = []
        self.pane_handle = object()

    def prepare_pane_handle(self, session_name, window_name):
        self.prepared_for = (session_name, window_name)
        return self.pane_handle

    def dismiss_resume_confirmation_modal_if_present(self, pane_handle):
        self.dismiss_calls += 1

    def wait_for_claude_prompt(self, pane_handle):
        return True

    def send_prompt_to_pane(self, pane_handle, content):
        self.prompts_sent.append(content)
        return True


def test_find_agent_wrapper_process_id_returns_first_match(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: _CompletedProcessStub("4242\n"),
    )
    assert resume_nudge.find_agent_wrapper_process_id("bronze") == 4242


def test_find_agent_wrapper_process_id_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: _CompletedProcessStub(""),
    )
    assert resume_nudge.find_agent_wrapper_process_id("bronze") is None


def test_agent_wrapper_has_live_claude_child_detects_claude(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: _CompletedProcessStub(
            "65068 claude\n65069 python3.12\n"
        ),
    )
    assert resume_nudge.agent_wrapper_has_live_claude_child(32060) is True


def test_agent_wrapper_has_live_claude_child_false_when_wrapper_sleeping(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: _CompletedProcessStub(""),
    )
    assert resume_nudge.agent_wrapper_has_live_claude_child(3884) is False


def test_agent_has_live_claude_repl_false_when_no_wrapper(monkeypatch):
    monkeypatch.setattr(
        resume_nudge, "find_agent_wrapper_process_id", lambda agent_name: None
    )
    assert resume_nudge.agent_has_live_claude_repl("alpha-pm") is False


def test_main_skips_injection_when_agent_dormant(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.sys,
        "argv",
        ["clawde-resume-nudge", "--session", "clawde", "--window", "alpha-pm"],
    )
    monkeypatch.setattr(
        resume_nudge, "wait_for_live_claude_repl", lambda agent_name: False
    )
    fake_backend = _FakeBackend()
    monkeypatch.setattr(resume_nudge, "select_heartbeat_backend", lambda: fake_backend)
    resume_nudge.main()
    assert fake_backend.prompts_sent == []


def test_main_injects_when_agent_has_live_claude(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.sys,
        "argv",
        ["clawde-resume-nudge", "--session", "clawde", "--window", "bronze"],
    )
    monkeypatch.setattr(
        resume_nudge, "wait_for_live_claude_repl", lambda agent_name: True
    )
    fake_backend = _FakeBackend()
    monkeypatch.setattr(resume_nudge, "select_heartbeat_backend", lambda: fake_backend)
    resume_nudge.main()
    assert fake_backend.prepared_for == ("clawde", "bronze")
    assert fake_backend.prompts_sent == [resume_nudge.RESUME_NUDGE_PROMPT]


def test_main_discards_inherited_pane_id_so_target_resolves_by_agent_label(monkeypatch):
    monkeypatch.setenv("HERDR_PANE_ID", "wW:p14")
    monkeypatch.setattr(
        resume_nudge.sys,
        "argv",
        ["clawde-resume-nudge", "--session", "clawde", "--window", "bronze"],
    )
    monkeypatch.setattr(
        resume_nudge, "wait_for_live_claude_repl", lambda agent_name: True
    )
    observed_ambient_pane_id_at_prepare = {}

    class _AmbientPaneRecordingBackend(_FakeBackend):
        def prepare_pane_handle(self, session_name, window_name):
            observed_ambient_pane_id_at_prepare["value"] = os.environ.get(
                "HERDR_PANE_ID"
            )
            return super().prepare_pane_handle(session_name, window_name)

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


def test_main_dismisses_resume_confirmation_modal_before_injecting(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.sys,
        "argv",
        ["clawde-resume-nudge", "--session", "clawde", "--window", "steward"],
    )
    monkeypatch.setattr(
        resume_nudge, "wait_for_live_claude_repl", lambda agent_name: True
    )
    fake_backend = _FakeBackend()
    monkeypatch.setattr(resume_nudge, "select_heartbeat_backend", lambda: fake_backend)
    resume_nudge.main()
    assert fake_backend.dismiss_calls == 1, (
        "a warm redeploy must answer any resume-confirmation dialog before injecting "
        "so the agent reaches its REPL instead of wedging at the dialog"
    )
    assert fake_backend.prompts_sent == [resume_nudge.RESUME_NUDGE_PROMPT]
