{
  pkgs,
  lib,
  homeDir,
}:
let
  secretsDirectory = "${homeDir}/.secrets";

  waitForSecretScript = pkgs.writeShellScript "wait-for-discord-bot-token-secret" (
    builtins.readFile ./scripts/wait-for-secret.sh
  );

  discordChannelEnvDirectoryFor = name: "${homeDir}/.claude/channels/discord/${name}";

  bridgePythonEnvironment = pkgs.python312.withPackages (pythonPackages: [
    pythonPackages.discordpy
  ]);

  discordBridgeIdentifyingArgumentsFor =
    name: "--agent-name ${lib.escapeShellArg name} --launch-config";

  discordBridgeProcessMatchPatternFor =
    name: "bridge.py ${discordBridgeIdentifyingArgumentsFor name}";

  discordBridgeCommandFor =
    {
      name,
      agent,
      workspaceDirectory,
      launchConfigPath,
    }:
    let
      tokenFile = lib.escapeShellArg "${secretsDirectory}/${toString agent.channel.discord.botTokenSecretName}";
      hasToken = agent.channel.discord.botTokenSecretName != null;
      waitForTokenPrefix = lib.optionalString hasToken "${waitForSecretScript} ${tokenFile} && ";
      tokenAssignment = lib.optionalString hasToken "DISCORD_BOT_TOKEN=$(cat ${tokenFile}) ";
      rotationFlag = lib.optionalString agent.dailySessionRotation "--daily-session-rotation";
      bridgeArguments = lib.concatStringsSep " " [
        "${./scripts/bridge.py} ${discordBridgeIdentifyingArgumentsFor name} ${lib.escapeShellArg launchConfigPath}"
        "--workspace-directory ${lib.escapeShellArg workspaceDirectory}"
        "--state-directory ${lib.escapeShellArg (discordChannelEnvDirectoryFor name)}"
        rotationFlag
      ];
    in
    "${waitForTokenPrefix}${tokenAssignment}PYTHONPATH=${./scripts}:${../../scripts/harness} exec ${bridgePythonEnvironment}/bin/python3 ${bridgeArguments}";
in
{
  inherit
    waitForSecretScript
    discordChannelEnvDirectoryFor
    discordBridgeProcessMatchPatternFor
    discordBridgeCommandFor
    ;
}
