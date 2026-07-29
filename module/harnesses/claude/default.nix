{
  pkgs,
  config,
  lib,
  ...
}:
let
  cfg = config.clawde;
  agentsOnClaude = lib.filterAttrs (_: agent: agent.harness == "claude") cfg.agents;
  hasClaudeAgents = agentsOnClaude != { };

  seedClaudeWorkspaceScript = pkgs.writeShellScript "seed-one-workspace-claude" (
    builtins.readFile ./scripts/seed-claude-workspace.sh
  );
in
{
  config = {
    clawde.harnesses.claude = {
      defaultModel = "sonnet";

      meaningfulOutputLinePattern = "^⏺ ";

      unenforceableDenyToolPatternsFor = _: [ ];

      supportedChannelTypes = [
        "none"
        "discord"
      ];

      runtimeProfile = {
        liveProcessNameFragment = "claude";

        idlePromptLinePatterns = [
          "^\\s*❯\\s*$"
          "\\s❯\\s*$"
          "^❯\\xa0"
        ];

        onboardingIndicators = [
          "Select login method"
          "Choose the text style"
          "Paste code here"
          "Claude account with subscription"
        ];

        usageLimitIndicators = [
          "Wait for limit to reset"
          "Adjust monthly spend limit"
          "You've hit your weekly limit"
        ];

        missingResumeSessionIndicators = [
          "No conversation found with session ID"
        ];

        prePromptModals = [
          {
            indicators = [
              "Resuming the full session will consume"
              "Resume full session as-is"
            ];
            dismissKey = "Enter";
          }
        ];

        sessionIdentity = {
          generatesIdentifier = true;
          freshArgvTemplate = "--session-id {session_identifier}";
          resumeArgvTemplate = "--resume {session_identifier}";
        };

        sessionTranscriptStore = {
          directoryTemplate = "~/.claude/projects/{workspace_slug}";
          fileNameTemplate = "{session_identifier}.jsonl";
        };
      };

      buildLaunchCommandFor =
        {
          name,
          agent,
          instructionsFile,
          sessionArgvShellExpansion,
          channelLaunchFlags,
          ...
        }:
        let
          inherit (cfg.harnesses.claude) binaryName;
          modelFlag = "--model ${agent.model}";
          nameFlag = "--name ${name}";
          permissionModeFlag = "--permission-mode ${agent.permissionMode}";
          skillDirectoryFlags = lib.concatMapStringsSep " " (
            directory: "--add-dir ${directory}"
          ) agent.skillDirectories;
          appendSystemPromptFlag = "--append-system-prompt \"$(cat ${instructionsFile})\"";
          mcpConfigFlags = lib.optionalString (
            agent.mcpConfigFile != null
          ) "--strict-mcp-config --mcp-config ${agent.mcpConfigFile} ";
        in
        "${binaryName} ${sessionArgvShellExpansion} ${channelLaunchFlags} ${modelFlag} ${nameFlag} ${permissionModeFlag} ${mcpConfigFlags}${appendSystemPromptFlag} ${skillDirectoryFlags}";

      buildRunOnceCommandFor =
        {
          name,
          agent,
          instructionsFile,
          ...
        }:
        let
          inherit (cfg.harnesses.claude) binaryName;
          runOncePrintFlag = "--print ${lib.escapeShellArg agent.heartbeatPrompt}";
          modelFlag = "--model ${agent.model}";
          nameFlag = "--name ${name}";
          permissionModeFlag = "--permission-mode ${agent.permissionMode}";
          skillDirectoryFlags = lib.concatMapStringsSep " " (
            directory: "--add-dir ${directory}"
          ) agent.skillDirectories;
          appendSystemPromptFlag = "--append-system-prompt \"$(cat ${instructionsFile})\"";
          mcpConfigFlags = lib.optionalString (
            agent.mcpConfigFile != null
          ) "--strict-mcp-config --mcp-config ${agent.mcpConfigFile} ";
        in
        "${binaryName} ${runOncePrintFlag} \${CLAWDE_SESSION_ARGV:-} ${modelFlag} ${nameFlag} ${permissionModeFlag} ${mcpConfigFlags}${appendSystemPromptFlag} ${skillDirectoryFlags}";

      workspaceFilesFor =
        {
          agent,
          workspaceRelativeToHome,
          channelWorkspaceSettings,
          ...
        }:
        let
          denySettings = lib.optionalAttrs (agent.denyToolPatterns != [ ]) {
            permissions.deny = agent.denyToolPatterns;
          };
          settings = lib.recursiveUpdate denySettings channelWorkspaceSettings;
        in
        lib.optionalAttrs (settings != { }) {
          "${workspaceRelativeToHome}/.claude/settings.json".text = builtins.toJSON settings;
        };

      agentActivationScriptFor =
        { workspaceDirectory, harnessBinary, ... }:
        "${seedClaudeWorkspaceScript} ${lib.escapeShellArg workspaceDirectory} ${lib.escapeShellArg harnessBinary}";
    };

    assertions = lib.optionals hasClaudeAgents [
      {
        assertion = cfg.harnesses.claude.package != null;
        message = "clawde: agents ${lib.concatStringsSep ", " (builtins.attrNames agentsOnClaude)} run on the claude harness, so clawde.harnesses.claude.package must be set by the consuming configuration.";
      }
    ];
  };
}
