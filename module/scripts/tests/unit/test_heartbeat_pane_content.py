import importlib.util
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def _load_pane_content_module():
    sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / "pane_content.py"
    module_spec = importlib.util.spec_from_file_location("pane_content", module_path)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules["pane_content"] = module
    module_spec.loader.exec_module(module)
    return module


pane_content = _load_pane_content_module()


def test_pane_at_repl_prompt_detects_bare_marker():
    assert pane_content.pane_is_at_claude_repl_prompt("some output\n❯\n")
    assert pane_content.pane_is_at_claude_repl_prompt("prefixed line ❯")


def test_pane_with_empty_prompt_and_trailing_space_is_idle():
    assert pane_content.pane_is_at_claude_repl_prompt("some output\n❯ \n")


def test_pane_with_autosuggestion_ghost_is_idle():
    pane_with_history_ghost = (
        "✻ Cooked for 39s\n"
        "──── steward ──\n"
        "❯\xa0Leave the submodule, end the tick\n"
        "────\n"
    )
    assert pane_content.pane_is_at_claude_repl_prompt(pane_with_history_ghost)


def test_pane_with_real_typed_input_is_not_idle():
    pane_with_pending_input = "some output\n❯ git status\n"
    assert not pane_content.pane_is_at_claude_repl_prompt(pane_with_pending_input)


def test_pane_at_onboarding_is_not_treated_as_idle_prompt():
    onboarding_pane = "Select login method\n❯ 1. Claude account with subscription"
    assert not pane_content.pane_is_at_claude_repl_prompt(onboarding_pane)


RESUME_CONFIRMATION_MODAL_PANE = (
    "This session is 13h 41m old and 111.2k tokens.\n"
    "\n"
    "Resuming the full session will consume a substantial portion of your usage "
    "limits. We recommend resuming from a summary.\n"
    "   1. Resume from summary (recommended)\n"
    "   2. Resume full session as-is\n"
    "   3. Don't ask me again\n"
    "Enter to confirm · Esc to cancel\n"
)


def test_resume_confirmation_modal_is_detected():
    assert pane_content.pane_indicates_resume_confirmation_modal(
        RESUME_CONFIRMATION_MODAL_PANE
    )


def test_ordinary_idle_prompt_is_not_a_resume_confirmation_modal():
    assert not pane_content.pane_indicates_resume_confirmation_modal("some output\n❯\n")


class _ScriptedCaptureBackend(pane_content.HeartbeatMultiplexerBackend):
    def __init__(self, captures):
        self._captures = list(captures)
        self.keys_sent = []
        self.prompts_sent = []

    def prepare_pane_handle(self, session_name, window_name):
        return "handle"

    def capture_recent_pane(self, pane_handle):
        return self._captures.pop(0) if self._captures else "❯\n"

    def send_single_key_to_pane(self, pane_handle, key):
        self.keys_sent.append(key)
        return True

    def send_prompt_to_pane(self, pane_handle, content):
        self.prompts_sent.append(content)
        return True


def test_pane_is_idle_reads_through_backend_capture():
    backend = _ScriptedCaptureBackend(["some work\n❯\n"])
    assert backend.pane_is_idle("handle")


def test_pane_is_not_idle_when_capture_shows_pending_input():
    backend = _ScriptedCaptureBackend(["some output\n❯ git status\n"])
    assert not backend.pane_is_idle("handle")


def test_dismiss_resume_modal_presses_enter_on_the_confirmation_dialog():
    backend = _ScriptedCaptureBackend([RESUME_CONFIRMATION_MODAL_PANE, "● back\n❯\n"])
    backend.dismiss_resume_confirmation_modal_if_present("handle")
    assert backend.keys_sent == ["Enter"]


def test_dismiss_resume_modal_is_a_noop_at_an_ordinary_prompt():
    backend = _ScriptedCaptureBackend(["● already home\n❯\n"])
    backend.dismiss_resume_confirmation_modal_if_present("handle")
    assert backend.keys_sent == []
