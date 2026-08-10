{
  pkgs,
  lib,
  module,
}:
let
  evaluation = import ./support/evaluation.nix { inherit pkgs lib module; };
  assertionSupport = import ./support/assertion.nix { inherit lib; };
  transportSupport = import ./transport-support.nix {
    inherit lib;
    inherit (assertionSupport) assertion stringify;
  };

  inherit (evaluation)
    evaluatedFor
    discordAgentConfig
    harnessLaunchCommandFor
    oneShotTurnCommandFor
    settingsTextFor
    instructionsFor
    sidecarProcessesFor
    ;
  inherit (assertionSupport)
    stringify
    assertion
    assertContains
    assertLacks
    failedAssertionMessagesFor
    ;
  inherit (transportSupport)
    transportAssertion
    satisfiableAssertion
    fakeEmbeddingHarness
    fakeBridgingHarness
    fakePassiveHarness
    ;

  claudeAutoEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "auto";
    lifetime = "agent";
  });

  claudeSidecarEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "sidecar";
    lifetime = "agent";
  });

  claudeSidecarServiceLifetimeEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "sidecar";
    lifetime = "service";
    dailySessionRotation = true;
  });

  codexSidecarEvaluated = evaluatedFor (discordAgentConfig {
    harness = "codex";
    transport = "auto";
    lifetime = "agent";
  });

  claudeEmbeddedWithMcpEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "embedded";
    lifetime = "agent";
    mcpServers = {
      fixture-server = { };
    };
  });

  claudeSidecarWithMcpEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "sidecar";
    lifetime = "agent";
    mcpServers = {
      fixture-server = { };
    };
  });

  claudeAutoSidecarProcess = builtins.head (sidecarProcessesFor claudeAutoEvaluated);
  claudeSidecarProcess = builtins.head (sidecarProcessesFor claudeSidecarEvaluated);
  claudeSidecarServiceLifetimeProcess = builtins.head (
    sidecarProcessesFor claudeSidecarServiceLifetimeEvaluated
  );
  codexSidecarProcess = builtins.head (sidecarProcessesFor codexSidecarEvaluated);

  claudeSidecarLaunchCommand = harnessLaunchCommandFor claudeSidecarEvaluated "claude";
  claudeAutoLaunchCommand = harnessLaunchCommandFor claudeAutoEvaluated "claude";
  codexLaunchCommand = harnessLaunchCommandFor codexSidecarEvaluated "codex";
  claudeSidecarOneShotCommand = oneShotTurnCommandFor claudeSidecarEvaluated "claude";
in
{
  inherit
    claudeAutoEvaluated
    claudeSidecarEvaluated
    claudeSidecarServiceLifetimeEvaluated
    codexSidecarEvaluated
    claudeEmbeddedWithMcpEvaluated
    claudeSidecarWithMcpEvaluated
    ;

  assertions = [
    (transportAssertion "auto-claude-resolves-embedded" "embedded" "auto" fakeEmbeddingHarness)
    (transportAssertion "auto-codex-resolves-sidecar" "sidecar" "auto" fakeBridgingHarness)
    (transportAssertion "forced-sidecar-on-embedding-harness" "none" "sidecar" fakeEmbeddingHarness)
    (transportAssertion "forced-embedded-on-bridging-harness" "none" "embedded" fakeBridgingHarness)
    (satisfiableAssertion "sidecar-on-passive-harness-unsatisfiable" "false" "sidecar"
      fakePassiveHarness
    )
    (satisfiableAssertion "embedded-on-bridging-harness-unsatisfiable" "false" "embedded"
      fakeBridgingHarness
    )
    (satisfiableAssertion "auto-on-passive-harness-unsatisfiable" "false" "auto" fakePassiveHarness)
    (assertion "embedded-strict-mcp-rejected" "true" (
      stringify (
        lib.any (message: builtins.match ".*mcpServers.*" message != null) (
          failedAssertionMessagesFor claudeEmbeddedWithMcpEvaluated
        )
      )
    ))
    (assertion "sidecar-strict-mcp-permitted" "true" (
      stringify ((failedAssertionMessagesFor claudeSidecarWithMcpEvaluated) == [ ])
    ))
    (assertion "auto-claude-sidecar-enabled" "false" (stringify claudeAutoSidecarProcess.enabled))
    (assertion "auto-claude-sidecar-lifetime" "agent" claudeAutoSidecarProcess.lifetime)
    (assertContains "auto-claude-keeps-plugin-launch-flags"
      "--channels plugin:discord@claude-plugins-official"
      claudeAutoLaunchCommand
    )
    (assertContains "auto-claude-keeps-token-environment" "DISCORD_BOT_TOKEN" claudeAutoLaunchCommand)
    (assertContains "auto-claude-keeps-plugin-workspace-settings" "discord@claude-plugins-official" (
      settingsTextFor claudeAutoEvaluated
    ))
    (assertContains "auto-claude-keeps-reply-stop-hook" "enforce-discord-reply-stop-hook" (
      settingsTextFor claudeAutoEvaluated
    ))
    (assertContains "auto-claude-instructions-use-reply-tool" "reply tool" (
      instructionsFor claudeAutoEvaluated
    ))
    (assertion "claude-sidecar-enabled" "true" (stringify claudeSidecarProcess.enabled))
    (assertion "claude-sidecar-lifetime" "agent" claudeSidecarProcess.lifetime)
    (assertContains "claude-sidecar-bridge-follows-the-launch-config" "--launch-config"
      claudeSidecarProcess.command
    )
    (assertContains "claude-sidecar-bridge-identifies-the-agent" "--agent-name fixture-agent"
      claudeSidecarProcess.command
    )
    (assertContains "claude-one-shot-command-runs-print-mode" "--print" claudeSidecarOneShotCommand)
    (assertContains "claude-one-shot-command-carries-session-identifier"
      "CLAWDE_CHANNEL_SESSION_IDENTIFIER"
      claudeSidecarOneShotCommand
    )
    (assertContains "claude-one-shot-command-resumes-explicitly" "--resume" claudeSidecarOneShotCommand)
    (assertContains "claude-one-shot-command-starts-fresh-explicitly" "--session-id"
      claudeSidecarOneShotCommand
    )
    (assertContains "claude-one-shot-command-writes-the-reply-file" "CLAWDE_CHANNEL_REPLY_FILE"
      claudeSidecarOneShotCommand
    )
    (assertLacks "claude-sidecar-launch-command-drops-plugin-flags"
      "--channels plugin:discord@claude-plugins-official"
      claudeSidecarLaunchCommand
    )
    (assertLacks "claude-sidecar-launch-command-drops-token-environment" "DISCORD_BOT_TOKEN"
      claudeSidecarLaunchCommand
    )
    (assertLacks "claude-sidecar-drops-plugin-workspace-settings" "enabledPlugins" (
      settingsTextFor claudeSidecarEvaluated
    ))
    (assertContains "claude-sidecar-instructions-use-plain-text-reply" "plain text" (
      instructionsFor claudeSidecarEvaluated
    ))
    (assertion "service-lifetime-sidecar-lifetime" "service"
      claudeSidecarServiceLifetimeProcess.lifetime
    )
    (assertContains "service-lifetime-sidecar-carries-rotation-flag" "--daily-session-rotation"
      claudeSidecarServiceLifetimeProcess.command
    )
    (assertLacks "agent-lifetime-sidecar-omits-rotation-flag" "--daily-session-rotation"
      claudeSidecarProcess.command
    )
    (assertion "codex-auto-sidecar-enabled" "true" (stringify codexSidecarProcess.enabled))
    (assertion "codex-auto-sidecar-lifetime" "agent" codexSidecarProcess.lifetime)
    (assertLacks "codex-launch-command-drops-plugin-flags"
      "--channels plugin:discord@claude-plugins-official"
      codexLaunchCommand
    )
    (assertContains "embedded-agents-keep-marketplace-preactivation" "run" (
      claudeAutoEvaluated.config.clawde.channelAdapters.discord.preActivation or ""
    ))
    (assertion "sidecar-agents-skip-marketplace-preactivation" "null" (
      stringify (claudeSidecarEvaluated.config.clawde.channelAdapters.discord.preActivation or null)
    ))
    (assertion "all-sidecar-fleet-skips-marketplace-preactivation" "null" (
      stringify (codexSidecarEvaluated.config.clawde.channelAdapters.discord.preActivation or null)
    ))
  ];
}
