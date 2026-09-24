{
  cfg,
  lib,
  pkgs,
  unshadowedBinaryPathAssignment,
  agentScopedMcpConfigFlagsFor,
}:
{
  name,
  agent,
  instructionsFile,
  ...
}:
let
  inherit (cfg.harnesses.claude) binaryInvocation;
  printFlag = "--print \"$CLAWDE_CHANNEL_PROMPT\" --output-format json --json-schema ${lib.escapeShellArg (builtins.readFile ../../lib/channel-reply-schema.json)}";
  channelSessionArguments = "\$(if [ -n \"\$CLAWDE_CHANNEL_SESSION_IDENTIFIER\" ]; then if [ -n \"\$CLAWDE_CHANNEL_SESSION_CONTINUATION\" ]; then printf -- '--resume %s' \"\$CLAWDE_CHANNEL_SESSION_IDENTIFIER\"; else printf -- '--session-id %s' \"\$CLAWDE_CHANNEL_SESSION_IDENTIFIER\"; fi; fi)";
  modelFlag = "--model ${agent.model}";
  nameFlag = "--name ${name}";
  permissionModeFlag = "--permission-mode ${agent.permissionMode}";
  skillDirectoryFlags = lib.concatMapStringsSep " " (
    directory: "--add-dir ${directory}"
  ) agent.skillDirectories;
  appendSystemPromptFlag = "--append-system-prompt \"$(cat ${instructionsFile})\"";
  mcpConfigFlags = agentScopedMcpConfigFlagsFor name agent;
in
"${unshadowedBinaryPathAssignment} ${binaryInvocation} ${printFlag} ${channelSessionArguments} ${modelFlag} ${nameFlag} ${permissionModeFlag} ${mcpConfigFlags}${appendSystemPromptFlag} ${skillDirectoryFlags} | ${pkgs.python312}/bin/python3 ${./scripts/extract-channel-reply.py} > \"\$CLAWDE_CHANNEL_REPLY_FILE\""
