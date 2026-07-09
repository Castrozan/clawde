import time

MAX_WAIT_ATTEMPTS = 90
INITIAL_DELAY_SECONDS = 30
REPL_PROMPT_MARKER = "❯"
AUTOSUGGESTION_GHOST_SEPARATOR = "\xa0"
ONBOARDING_INDICATORS = [
    "Select login method",
    "Choose the text style",
    "Paste code here",
    "Claude account with subscription",
]
RESUME_CONFIRMATION_MODAL_INDICATORS = [
    "Resuming the full session will consume",
    "Resume full session as-is",
]
RESUME_MODAL_DISMISS_MAX_ATTEMPTS = 15
RESUME_MODAL_DISMISS_DELAY_SECONDS = 2
RESUME_MODAL_SUMMARY_RESUME_KEY = "Enter"


def pane_is_at_onboarding(pane_content: str) -> bool:
    return any(indicator in pane_content for indicator in ONBOARDING_INDICATORS)


def pane_indicates_resume_confirmation_modal(pane_content: str) -> bool:
    return all(
        indicator in pane_content for indicator in RESUME_CONFIRMATION_MODAL_INDICATORS
    )


def line_is_idle_repl_prompt(line: str) -> bool:
    stripped = line.strip()
    if stripped == REPL_PROMPT_MARKER or stripped.endswith(" " + REPL_PROMPT_MARKER):
        return True
    return line.startswith(REPL_PROMPT_MARKER + AUTOSUGGESTION_GHOST_SEPARATOR)


def pane_is_at_claude_repl_prompt(pane_content: str) -> bool:
    if pane_is_at_onboarding(pane_content):
        return False
    return any(line_is_idle_repl_prompt(line) for line in pane_content.splitlines())


class HeartbeatMultiplexerBackend:
    def prepare_pane_handle(self, session_name: str, window_name: str):
        raise NotImplementedError

    def capture_recent_pane(self, pane_handle) -> str | None:
        raise NotImplementedError

    def send_single_key_to_pane(self, pane_handle, key: str) -> bool:
        raise NotImplementedError

    def send_prompt_to_pane(self, pane_handle, content: str) -> bool:
        raise NotImplementedError

    def wait_for_claude_prompt(self, pane_handle) -> bool:
        time.sleep(INITIAL_DELAY_SECONDS)

        for _ in range(MAX_WAIT_ATTEMPTS):
            content = self.capture_recent_pane(pane_handle)
            if content is not None:
                if pane_is_at_onboarding(content):
                    time.sleep(5)
                    continue
                if pane_is_at_claude_repl_prompt(content):
                    return True
            time.sleep(2)
        return False

    def wait_until_agent_is_past_pre_prompt_gates(self, pane_handle) -> bool:
        time.sleep(INITIAL_DELAY_SECONDS)

        for _ in range(MAX_WAIT_ATTEMPTS):
            content = self.capture_recent_pane(pane_handle)
            if content is not None:
                if pane_is_at_onboarding(content):
                    time.sleep(5)
                    continue
                if pane_indicates_resume_confirmation_modal(content):
                    self.send_single_key_to_pane(
                        pane_handle, RESUME_MODAL_SUMMARY_RESUME_KEY
                    )
                    time.sleep(RESUME_MODAL_DISMISS_DELAY_SECONDS)
                    continue
                return True
            time.sleep(2)
        return False

    def pane_is_idle(self, pane_handle) -> bool:
        content = self.capture_recent_pane(pane_handle)
        return content is not None and pane_is_at_claude_repl_prompt(content)

    def dismiss_resume_confirmation_modal_if_present(self, pane_handle) -> None:
        for _ in range(RESUME_MODAL_DISMISS_MAX_ATTEMPTS):
            pane_content = self.capture_recent_pane(pane_handle)
            if pane_content is None:
                time.sleep(RESUME_MODAL_DISMISS_DELAY_SECONDS)
                continue
            if pane_is_at_claude_repl_prompt(pane_content):
                return
            if pane_indicates_resume_confirmation_modal(pane_content):
                self.send_single_key_to_pane(
                    pane_handle, RESUME_MODAL_SUMMARY_RESUME_KEY
                )
                return
            time.sleep(RESUME_MODAL_DISMISS_DELAY_SECONDS)
