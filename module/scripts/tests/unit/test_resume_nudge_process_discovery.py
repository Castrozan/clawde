from resume_nudge_test_support import CompletedProcessStub, load_resume_nudge_module

resume_nudge = load_resume_nudge_module()


def test_find_agent_wrapper_process_id_returns_first_match(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcessStub("4242\n"),
    )
    assert resume_nudge.find_agent_wrapper_process_id("bronze") == 4242


def test_find_agent_wrapper_process_id_returns_none_when_absent(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcessStub(""),
    )
    assert resume_nudge.find_agent_wrapper_process_id("bronze") is None


def test_live_harness_child_is_detected_by_the_harness_process_fragment(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcessStub(
            "65068 claude\n65069 python3.12\n"
        ),
    )
    assert resume_nudge.agent_wrapper_has_live_harness_child(32060, "claude") is True


def test_a_live_child_of_another_harness_does_not_count(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcessStub(
            "65068 claude\n65069 python3.12\n"
        ),
    )
    assert resume_nudge.agent_wrapper_has_live_harness_child(32060, "codex") is False


def test_live_harness_child_false_when_wrapper_sleeping(monkeypatch):
    monkeypatch.setattr(
        resume_nudge.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcessStub(""),
    )
    assert resume_nudge.agent_wrapper_has_live_harness_child(3884, "claude") is False


def test_agent_has_live_harness_repl_false_when_no_wrapper(monkeypatch):
    monkeypatch.setattr(
        resume_nudge, "find_agent_wrapper_process_id", lambda agent_name: None
    )
    assert resume_nudge.agent_has_live_harness_repl("alpha-pm", "claude") is False
