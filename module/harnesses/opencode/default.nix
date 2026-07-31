{
  config,
  lib,
  ...
}:
let
  cfg = config.clawde;
  homeDir = config.home.homeDirectory;
  runtimeLocations = import ../../lib/runtime-locations.nix { inherit homeDir; };

  agentsOnOpencode = lib.filterAttrs (_: agent: agent.harness == "opencode") cfg.agents;
  hasOpencodeAgents = agentsOnOpencode != { };

  harnessHomeRelativeToHome =
    name: "${runtimeLocations.runtimeRootRelativeToHome}/harness-home/opencode/${name}";

  agentConfigurationRelativeToHome = name: "${harnessHomeRelativeToHome name}/opencode.json";
  agentConfigurationFile = name: "${homeDir}/${agentConfigurationRelativeToHome name}";

  unshadowedBinaryDirectoryRelativeToHome = "${runtimeLocations.runtimeRootRelativeToHome}/harness-home/opencode/bin";
  unshadowedBinaryDirectory = "${homeDir}/${unshadowedBinaryDirectoryRelativeToHome}";
  unshadowedBinaryPathAssignment = "PATH=${lib.escapeShellArg unshadowedBinaryDirectory}:\"$PATH\"";

  denyToolPatternTranslation = import ./deny-tool-pattern-translation.nix;

  claudeLayoutSkillsSubdirectory = skillSetDirectory: "${skillSetDirectory}/.claude/skills";

  defaultAgentDefinitionName = "build";

  buildPermissionMapFor = agent: {
    bash = denyToolPatternTranslation.bashPermissionRuleFor agent.denyToolPatterns;
    skill = denyToolPatternTranslation.skillPermissionRuleFor agent.denyToolPatterns;
    edit = "allow";
    read = "allow";
    glob = "allow";
    grep = "allow";
    list = "allow";
    task = "allow";
    lsp = "allow";
    external_directory = "allow";
    todowrite = "allow";
    webfetch = "allow";
    websearch = "allow";
    doom_loop = "allow";
    question = "allow";
  };

  buildOpencodeConfigurationFor =
    name: agent:
    let
      permissionMap = buildPermissionMapFor agent;
    in
    {
      "$schema" = "https://opencode.ai/config.json";
      autoupdate = false;
      share = "disabled";
      inherit (agent) model;
      instructions = [ (runtimeLocations.agentInstructionsFile name) ];
      permission = permissionMap;
      mcp = if agent.mcpServers == null then { } else agent.mcpServers;

      agent.${defaultAgentDefinitionName} = {
        inherit (agent) model;
        mode = "primary";
        variant = agent.reasoningEffort;
        permission = permissionMap;
      };
    }
    // lib.optionalAttrs (agent.skillDirectories != [ ]) {
      skills.paths = map claudeLayoutSkillsSubdirectory agent.skillDirectories;
    };
in
{
  config = {
    clawde.harnesses.opencode = {
      defaultModel = "opencode/deepseek-v4-flash-free";

      meaningfulOutputLinePattern = "^\\s*▣\\s+";

      supportedChannelTypes = [ "none" ];

      inherit (denyToolPatternTranslation) unenforceableDenyToolPatternsFor;

      runtimeProfile = {
        liveProcessNameFragment = "opencode";

        idlePromptLinePatterns = [ "^(?!.*esc interrupt).*ctrl\\+p commands" ];

        onboardingIndicators = [
          "Select a provider"
          "Sign in with"
          "No credentials found"
          "opencode auth login"
        ];

        usageLimitIndicators = [
          "You have exceeded your usage limit"
          "rate limit exceeded"
          "quota exceeded"
        ];

        sessionIdentity = {
          generatesIdentifier = false;
          freshArgvTemplate = "";
          resumeArgvTemplate = "--continue";
        };
      };

      buildLaunchCommandFor =
        {
          name,
          sessionArgvShellExpansion,
          ...
        }:
        let
          inherit (cfg.harnesses.opencode) binaryName;
          configurationAssignment = "OPENCODE_CONFIG=${lib.escapeShellArg (agentConfigurationFile name)}";
        in
        "${unshadowedBinaryPathAssignment} ${configurationAssignment} ${binaryName} ${sessionArgvShellExpansion}";

      buildRunOnceCommandFor =
        {
          name,
          agent,
          ...
        }:
        let
          inherit (cfg.harnesses.opencode) binaryName;
          configurationAssignment = "OPENCODE_CONFIG=${lib.escapeShellArg (agentConfigurationFile name)}";
        in
        "${unshadowedBinaryPathAssignment} ${configurationAssignment} ${binaryName} run ${lib.escapeShellArg agent.heartbeatPrompt}";

      workspaceFilesFor =
        { name, agent, ... }:
        {
          "${agentConfigurationRelativeToHome name}".text = builtins.toJSON (
            buildOpencodeConfigurationFor name agent
          );
        };
    };

    home.file = lib.optionalAttrs (hasOpencodeAgents && cfg.harnesses.opencode.package != null) {
      "${unshadowedBinaryDirectoryRelativeToHome}/${cfg.harnesses.opencode.binaryName}".source =
        "${cfg.harnesses.opencode.package}/bin/${cfg.harnesses.opencode.binaryName}";
    };

    assertions = lib.optionals hasOpencodeAgents [
      {
        assertion = cfg.harnesses.opencode.package != null;
        message = "clawde: agents ${lib.concatStringsSep ", " (builtins.attrNames agentsOnOpencode)} run on the opencode harness, so clawde.harnesses.opencode.package must be set by the consuming configuration.";
      }
    ];
  };
}
