_: {
  serializeHarnessRuntimeProfile = harnessName: runtimeProfile: {
    harness_name = harnessName;
    live_process_name_fragment = runtimeProfile.liveProcessNameFragment;
    idle_prompt_line_patterns = runtimeProfile.idlePromptLinePatterns;
    onboarding_indicators = runtimeProfile.onboardingIndicators;
    usage_limit_indicators = runtimeProfile.usageLimitIndicators;
    missing_resume_session_indicators = runtimeProfile.missingResumeSessionIndicators;
    pre_prompt_modals = map (modal: {
      inherit (modal) indicators;
      dismiss_key = modal.dismissKey;
    }) runtimeProfile.prePromptModals;
    session_identity = {
      generates_identifier = runtimeProfile.sessionIdentity.generatesIdentifier;
      fresh_argv_template = runtimeProfile.sessionIdentity.freshArgvTemplate;
      resume_argv_template = runtimeProfile.sessionIdentity.resumeArgvTemplate;
    };
    session_transcript_store = {
      directory_template = runtimeProfile.sessionTranscriptStore.directoryTemplate;
      file_name_template = runtimeProfile.sessionTranscriptStore.fileNameTemplate;
    };
  };
}
