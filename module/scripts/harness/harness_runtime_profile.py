import json
import os
import re

from active_harness import (
    active_harness_name_for_launch_config,
    active_runtime_profile_mapping,
)

SESSION_IDENTIFIER_TEMPLATE_PLACEHOLDER = "{session_identifier}"
WORKSPACE_SLUG_TEMPLATE_PLACEHOLDER = "{workspace_slug}"
NON_ALPHANUMERIC_CHARACTER = re.compile(r"[^a-zA-Z0-9]")


class HarnessRuntimeProfile:
    def __init__(self, profile_mapping: dict):
        self.harness_name = profile_mapping["harness_name"]
        self.live_process_name_fragment = profile_mapping["live_process_name_fragment"]
        self.idle_prompt_line_patterns = [
            re.compile(pattern)
            for pattern in profile_mapping.get("idle_prompt_line_patterns", [])
        ]
        self.onboarding_indicators = profile_mapping.get("onboarding_indicators", [])
        self.usage_limit_indicators = profile_mapping.get("usage_limit_indicators", [])
        self.missing_resume_session_indicators = profile_mapping.get(
            "missing_resume_session_indicators", []
        )
        self.pre_prompt_modals = profile_mapping.get("pre_prompt_modals", [])
        session_identity = profile_mapping.get("session_identity", {})
        self.generates_session_identifier = session_identity.get(
            "generates_identifier", False
        )
        self.fresh_session_argv_template = session_identity.get(
            "fresh_argv_template", ""
        )
        self.resume_session_argv_template = session_identity.get(
            "resume_argv_template", ""
        )
        transcript_store = profile_mapping.get("session_transcript_store", {})
        self.transcript_directory_template = transcript_store.get(
            "directory_template", ""
        )
        self.transcript_file_name_template = transcript_store.get(
            "file_name_template", ""
        )

    def pane_is_at_onboarding(self, pane_content: str) -> bool:
        return any(
            indicator in pane_content for indicator in self.onboarding_indicators
        )

    def pane_indicates_usage_limit_modal(self, pane_content: str) -> bool:
        return any(
            indicator in pane_content for indicator in self.usage_limit_indicators
        )

    def pane_indicates_missing_resume_session(self, pane_content: str) -> bool:
        return any(
            indicator in pane_content
            for indicator in self.missing_resume_session_indicators
        )

    def pane_is_at_idle_prompt(self, pane_content: str) -> bool:
        if self.pane_is_at_onboarding(pane_content):
            return False
        return any(
            pattern.search(line)
            for line in pane_content.splitlines()
            for pattern in self.idle_prompt_line_patterns
        )

    def matching_pre_prompt_modal(self, pane_content: str) -> dict | None:
        for modal in self.pre_prompt_modals:
            indicators = modal.get("indicators", [])
            if indicators and all(
                indicator in pane_content for indicator in indicators
            ):
                return modal
        return None

    def render_session_argv(
        self, session_identifier: str | None, resuming: bool
    ) -> str:
        template = (
            self.resume_session_argv_template
            if resuming
            else self.fresh_session_argv_template
        )
        if session_identifier is None:
            return template
        return template.replace(
            SESSION_IDENTIFIER_TEMPLATE_PLACEHOLDER, session_identifier
        )

    def exposes_session_transcript_store(self) -> bool:
        return bool(
            self.transcript_directory_template and self.transcript_file_name_template
        )

    def render_session_transcript_path(
        self, session_identifier: str, workspace_directory: str
    ) -> str:
        workspace_slug = NON_ALPHANUMERIC_CHARACTER.sub("-", str(workspace_directory))
        directory = self.transcript_directory_template.replace(
            WORKSPACE_SLUG_TEMPLATE_PLACEHOLDER, workspace_slug
        )
        file_name = self.transcript_file_name_template.replace(
            SESSION_IDENTIFIER_TEMPLATE_PLACEHOLDER, session_identifier
        )
        return os.path.join(os.path.expanduser(directory), file_name)


def load_harness_runtime_profile_from_launch_config(launch_config_path: str):
    with open(launch_config_path) as launch_config_file:
        launch_config = json.load(launch_config_file)
    return HarnessRuntimeProfile(
        active_runtime_profile_mapping(
            launch_config,
            active_harness_name_for_launch_config(launch_config, launch_config_path),
        )
    )
