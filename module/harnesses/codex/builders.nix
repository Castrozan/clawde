{
  pkgs,
  lib,
  cfg,
  codexHomeRelativeToHome,
  codexHomeDirectory,
  channelBridgeHomeRelativeToHome,
  channelBridgeHomeDirectory,
  unshadowedBinaryPathAssignment,
  userCodexAuthenticationFile,
  seedCodexHarnessHomeScript,
  codexConfigurationTomlFormat,
  buildCodexConfigurationFor,
}:
let
  structuredReplyParserCommand = "${pkgs.python312}/bin/python3 ${./scripts/publish-codex-structured-reply.py}";
in
{
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
      structuredRawOutputPath = "\${CLAWDE_CHANNEL_REPLY_FILE}.codex-turns";
      codexReplySchema = ./reply-schema.json;
    in
    "${unshadowedBinaryPathAssignment} ${codexHomeAssignment} ${binaryInvocation} exec ${resumeSubcommand} --dangerously-bypass-approvals-and-sandbox --output-schema ${lib.escapeShellArg (builtins.toString codexReplySchema)} --output-last-message \"${structuredRawOutputPath}\" ${developerInstructionsFlag} \"$CLAWDE_CHANNEL_PROMPT\" && ${structuredReplyParserCommand} \"${structuredRawOutputPath}\" \"$CLAWDE_CHANNEL_REPLY_FILE\"";

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
}
