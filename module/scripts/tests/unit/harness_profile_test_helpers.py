from harness_runtime_profile import HarnessRuntimeProfile

CLAUDE_PROFILE_MAPPING = {
    "harness_name": "claude",
    "live_process_name_fragment": "claude",
    "idle_prompt_line_patterns": [
        "^\\s*❯\\s*$",
        "\\s❯\\s*$",
        "^❯\\xa0",
    ],
    "onboarding_indicators": [
        "Select login method",
        "Claude account with subscription",
    ],
    "usage_limit_indicators": [
        "Wait for limit to reset",
        "You've hit your weekly limit",
    ],
    "missing_resume_session_indicators": [
        "No conversation found with session ID",
    ],
    "pre_prompt_modals": [
        {
            "indicators": [
                "Resuming the full session will consume",
                "Resume full session as-is",
            ],
            "dismiss_key": "Enter",
        }
    ],
    "session_identity": {
        "generates_identifier": True,
        "fresh_argv_template": "--session-id {session_identifier}",
        "resume_argv_template": "--resume {session_identifier}",
    },
    "session_transcript_store": {
        "directory_template": "~/.claude/projects/{workspace_slug}",
        "file_name_template": "{session_identifier}.jsonl",
    },
}

CODEX_PROFILE_MAPPING = {
    "harness_name": "codex",
    "live_process_name_fragment": "codex",
    "idle_prompt_line_patterns": ["^\\s*Ready\\s·"],
    "onboarding_indicators": ["Do you trust the contents of this directory?"],
    "usage_limit_indicators": ["You've hit your usage limit"],
    "pre_prompt_modals": [
        {
            "indicators": [
                "Do you trust the contents of this directory?",
                "Yes, continue",
            ],
            "dismiss_key": "Enter",
        }
    ],
    "session_identity": {
        "generates_identifier": False,
        "fresh_argv_template": "",
        "resume_argv_template": "resume --last",
    },
    "session_transcript_store": {
        "directory_template": "",
        "file_name_template": "",
    },
}


OPENCODE_PROFILE_MAPPING = {
    "harness_name": "opencode",
    "live_process_name_fragment": "opencode",
    "idle_prompt_line_patterns": ["^(?!.*esc interrupt).*ctrl\\+p commands"],
    "onboarding_indicators": ["Select a provider", "opencode auth login"],
    "usage_limit_indicators": [
        "usage limit reached",
        "You have exceeded your usage limit",
        "rate limit exceeded",
        "quota exceeded",
    ],
    "session_identity": {
        "generates_identifier": False,
        "fresh_argv_template": "",
        "resume_argv_template": "--continue",
    },
    "session_transcript_store": {
        "directory_template": "",
        "file_name_template": "",
    },
}


def make_claude_profile() -> HarnessRuntimeProfile:
    return HarnessRuntimeProfile(CLAUDE_PROFILE_MAPPING)


def make_codex_profile() -> HarnessRuntimeProfile:
    return HarnessRuntimeProfile(CODEX_PROFILE_MAPPING)


def make_opencode_profile() -> HarnessRuntimeProfile:
    return HarnessRuntimeProfile(OPENCODE_PROFILE_MAPPING)


def harness_launch_config_block(profile_mapping, launch_command):
    harness_name = profile_mapping["harness_name"]
    return {
        "declared_harness": harness_name,
        "harness_launch_commands": {harness_name: launch_command},
        "harness_runtime_profiles": {harness_name: profile_mapping},
    }
