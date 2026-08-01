{
  pkgs,
  config,
  lib,
  ...
}:
let
  cfg = config.clawde;
  homeDir = config.home.homeDirectory;
  runtimeLocations = import ../../lib/runtime-locations.nix { inherit homeDir; };

  agentsOnCodex = lib.filterAttrs (_: agent: agent.harness == "codex") cfg.agents;
  hasCodexAgents = agentsOnCodex != { };

  codexHomeRelativeToHome =
    name: "${runtimeLocations.runtimeRootRelativeToHome}/harness-home/codex/${name}";
  codexHomeDirectory = name: "${homeDir}/${codexHomeRelativeToHome name}";

  channelBridgeHomeRelativeToHome = name: "${codexHomeRelativeToHome name}-channel";
  channelBridgeHomeDirectory = name: "${homeDir}/${channelBridgeHomeRelativeToHome name}";

  unshadowedBinaryDirectoryRelativeToHome = "${runtimeLocations.runtimeRootRelativeToHome}/harness-home/codex/bin";
  unshadowedBinaryDirectory = "${homeDir}/${unshadowedBinaryDirectoryRelativeToHome}";
  unshadowedBinaryPathAssignment = "PATH=${lib.escapeShellArg unshadowedBinaryDirectory}:\"$PATH\"";

  userCodexAuthenticationFile = "${homeDir}/.codex/auth.json";

  seedCodexHarnessHomeScript = pkgs.writeShellScript "seed-one-codex-harness-home" (
    builtins.readFile ./scripts/seed-codex-harness-home.sh
  );

  codexConfigurationTomlFormat = pkgs.formats.toml { };

  denyToolPatternReachability = import ./deny-tool-pattern-reachability.nix;

  runStateStatusLineSegment = "run-state";

  buildCodexConfigurationFor = agent: workspaceDirectory: {
    inherit (agent) model;
    model_reasoning_effort = agent.reasoningEffort;
    approval_policy = "never";
    sandbox_mode = "danger-full-access";
    suppress_unstable_features_warning = true;

    projects.${workspaceDirectory}.trust_level = "trusted";

    tui = {
      animations = false;
      show_tooltips = false;
      status_line = [
        runStateStatusLineSegment
        "model-with-reasoning"
        "context-used"
      ];
    };

    notice = {
      hide_full_access_warning = true;
      hide_rate_limit_model_nudge = true;
      hide_world_writable_warning = true;
      fast_default_opt_out = true;
    };

    mcp_servers = if agent.mcpServers == null then { } else agent.mcpServers;
  };
in
{
  config = {
    clawde.harnesses.codex = {
      defaultModel = "gpt-5.6-sol";

      meaningfulOutputLinePattern = "^• ";

      supportedChannelTypes = [
        "none"
        "discord"
      ];

      inherit (denyToolPatternReachability) unenforceableDenyToolPatternsFor;

      runtimeProfile = {
        liveProcessNameFragment = "codex";

        idlePromptLinePatterns = [ "^\\s*Ready\\s·" ];

        onboardingIndicators = [
          "Do you trust the contents of this directory?"
          "Sign in with ChatGPT"
          "Select a login method"
        ];

        usageLimitIndicators = [
          "You've hit your usage limit"
          "You have hit your usage limit"
          "Upgrade to Pro to keep going"
        ];

        prePromptModals = [
          {
            indicators = [
              "Do you trust the contents of this directory?"
              "Yes, continue"
            ];
            dismissKey = "Enter";
          }
        ];

        sessionIdentity = {
          generatesIdentifier = false;
          freshArgvTemplate = "";
          resumeArgvTemplate = "resume --last";
        };
      };

      buildLaunchCommandFor =
        {
          name,
          instructionsFile,
          sessionArgvShellExpansion,
          ...
        }:
        let
          inherit (cfg.harnesses.codex) binaryInvocation;
          codexHomeAssignment = "CODEX_HOME=${lib.escapeShellArg (codexHomeDirectory name)}";
          developerInstructionsFlag = "-c developer_instructions=\"$(cat ${instructionsFile})\"";
        in
        "${unshadowedBinaryPathAssignment} ${codexHomeAssignment} ${binaryInvocation} ${sessionArgvShellExpansion} --no-alt-screen --dangerously-bypass-hook-trust ${developerInstructionsFlag}";

      buildRunOnceCommandFor =
        {
          name,
          agent,
          instructionsFile,
          ...
        }:
        let
          inherit (cfg.harnesses.codex) binaryInvocation;
          codexHomeAssignment = "CODEX_HOME=${lib.escapeShellArg (codexHomeDirectory name)}";
          developerInstructionsFlag = "-c developer_instructions=\"$(cat ${instructionsFile})\"";
        in
        "${unshadowedBinaryPathAssignment} ${codexHomeAssignment} ${binaryInvocation} exec --dangerously-bypass-approvals-and-sandbox ${developerInstructionsFlag} ${lib.escapeShellArg agent.heartbeatPrompt}";

      buildOneShotTurnCommandFor =
        {
          name,
          instructionsFile,
          ...
        }:
        let
          inherit (cfg.harnesses.codex) binaryInvocation;
          codexHomeAssignment = "CODEX_HOME=${lib.escapeShellArg (channelBridgeHomeDirectory name)}";
          developerInstructionsFlag = "-c developer_instructions=\"$(cat ${instructionsFile})\"";
          resumeSubcommand = "\${CLAWDE_CHANNEL_SESSION_CONTINUATION:+resume --last}";
        in
        "${unshadowedBinaryPathAssignment} ${codexHomeAssignment} ${binaryInvocation} exec ${resumeSubcommand} --dangerously-bypass-approvals-and-sandbox --output-last-message \"$CLAWDE_CHANNEL_REPLY_FILE\" ${developerInstructionsFlag} \"$CLAWDE_CHANNEL_PROMPT\"";

      workspaceFilesFor =
        {
          name,
          agent,
          workspaceDirectory,
          ...
        }:
        {
          "${codexHomeRelativeToHome name}/config.toml".source =
            codexConfigurationTomlFormat.generate "clawde-codex-config-${name}.toml" (
              buildCodexConfigurationFor agent workspaceDirectory
            );
          "${channelBridgeHomeRelativeToHome name}/config.toml".source =
            codexConfigurationTomlFormat.generate "clawde-codex-channel-config-${name}.toml" (
              buildCodexConfigurationFor agent workspaceDirectory
            );
        };

      agentActivationScriptFor =
        { name, agent, ... }:
        lib.concatMapStringsSep "\n"
          (
            harnessHome:
            lib.concatStringsSep " " [
              seedCodexHarnessHomeScript
              (lib.escapeShellArg harnessHome)
              (lib.escapeShellArg userCodexAuthenticationFile)
              (lib.escapeShellArg (lib.concatStringsSep "\n" agent.skillDirectories))
            ]
          )
          [
            (codexHomeDirectory name)
            (channelBridgeHomeDirectory name)
          ];
    };

    home.file = lib.optionalAttrs (hasCodexAgents && cfg.harnesses.codex.package != null) {
      "${unshadowedBinaryDirectoryRelativeToHome}/${cfg.harnesses.codex.binaryName}".source =
        "${cfg.harnesses.codex.package}/bin/${cfg.harnesses.codex.binaryName}";
    };

    assertions = lib.optionals hasCodexAgents [
      {
        assertion = cfg.harnesses.codex.package != null;
        message = "clawde: agents ${lib.concatStringsSep ", " (builtins.attrNames agentsOnCodex)} run on the codex harness, so clawde.harnesses.codex.package must be set by the consuming configuration.";
      }
    ];
  };
}
