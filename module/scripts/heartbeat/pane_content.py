import time

MAX_WAIT_ATTEMPTS = 90
INITIAL_DELAY_SECONDS = 30
ONBOARDING_RECHECK_DELAY_SECONDS = 5
PANE_RECHECK_DELAY_SECONDS = 2
MODAL_DISMISS_MAX_ATTEMPTS = 15
MODAL_DISMISS_DELAY_SECONDS = 2


class HeartbeatMultiplexerBackend:
    def prepare_pane_handle(self, session_name: str, window_name: str):
        raise NotImplementedError

    def capture_recent_pane(self, pane_handle) -> str | None:
        raise NotImplementedError

    def send_single_key_to_pane(self, pane_handle, key: str) -> bool:
        raise NotImplementedError

    def send_prompt_to_pane(self, pane_handle, content: str) -> bool:
        raise NotImplementedError

    def wait_for_agent_prompt(self, pane_handle, harness_runtime_profile) -> bool:
        time.sleep(INITIAL_DELAY_SECONDS)

        for _ in range(MAX_WAIT_ATTEMPTS):
            content = self.capture_recent_pane(pane_handle)
            if content is not None:
                if harness_runtime_profile.pane_is_at_onboarding(content):
                    time.sleep(ONBOARDING_RECHECK_DELAY_SECONDS)
                    continue
                if harness_runtime_profile.pane_is_at_idle_prompt(content):
                    return True
            time.sleep(PANE_RECHECK_DELAY_SECONDS)
        return False

    def wait_until_agent_is_past_pre_prompt_gates(
        self, pane_handle, harness_runtime_profile
    ) -> bool:
        time.sleep(INITIAL_DELAY_SECONDS)

        for _ in range(MAX_WAIT_ATTEMPTS):
            content = self.capture_recent_pane(pane_handle)
            if content is not None:
                if harness_runtime_profile.pane_is_at_onboarding(content):
                    time.sleep(ONBOARDING_RECHECK_DELAY_SECONDS)
                    continue
                modal = harness_runtime_profile.matching_pre_prompt_modal(content)
                if modal is not None:
                    self.send_single_key_to_pane(pane_handle, modal["dismiss_key"])
                    time.sleep(MODAL_DISMISS_DELAY_SECONDS)
                    continue
                return True
            time.sleep(PANE_RECHECK_DELAY_SECONDS)
        return False

    def pane_reports_active_work(self, pane_handle) -> bool:
        return False

    def pane_is_idle(self, pane_handle, harness_runtime_profile) -> bool:
        content = self.capture_recent_pane(pane_handle)
        return content is not None and harness_runtime_profile.pane_is_at_idle_prompt(
            content
        )

    def dismiss_pre_prompt_modal_if_present(
        self, pane_handle, harness_runtime_profile
    ) -> None:
        for _ in range(MODAL_DISMISS_MAX_ATTEMPTS):
            pane_content = self.capture_recent_pane(pane_handle)
            if pane_content is None:
                time.sleep(MODAL_DISMISS_DELAY_SECONDS)
                continue
            if harness_runtime_profile.pane_is_at_idle_prompt(pane_content):
                return
            modal = harness_runtime_profile.matching_pre_prompt_modal(pane_content)
            if modal is not None:
                self.send_single_key_to_pane(pane_handle, modal["dismiss_key"])
                return
            time.sleep(MODAL_DISMISS_DELAY_SECONDS)
