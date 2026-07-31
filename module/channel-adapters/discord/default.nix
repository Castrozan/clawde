{
  pkgs,
  config,
  lib,
  ...
}:
let
  cfg = config.clawde;
  homeDir = config.home.homeDirectory;
  secretsDirectory = "${homeDir}/.secrets";
  agentsUsingDiscord = lib.filterAttrs (_: agent: agent.channel.type == "discord") cfg.agents;
  hasDiscordAgents = agentsUsingDiscord != { };

  discordAdapterInstructions = builtins.readFile ./instructions/discord-runtime.md;

  updateClaudePluginsMarketplace = pkgs.writeShellScript "update-claude-plugins-marketplace" ''
    export MARKETPLACE_DIR=${lib.escapeShellArg "${homeDir}/.claude/plugins/marketplaces/claude-plugins-official"}
    export GIT_BIN=${pkgs.git}/bin/git
    ${builtins.readFile ./scripts/update-claude-plugins-marketplace.sh}
  '';

  enforceDiscordReplyStopHook = pkgs.writeShellScript "enforce-discord-reply-stop-hook" ''
    exec ${pkgs.python312}/bin/python3 ${./scripts/enforce-discord-reply-stop-hook.py} "$@"
  '';

  injectOneSecretScript = pkgs.writeShellScript "inject-one-discord-bot-token" (
    builtins.readFile ../../scripts/inject-one-secret.sh
  );

  waitForSecretScript = pkgs.writeShellScript "wait-for-discord-bot-token-secret" (
    builtins.readFile ./scripts/wait-for-secret.sh
  );

  discordChannelEnvDirectoryFor = name: "${homeDir}/.claude/channels/discord/${name}";

  sharedDiscordAccessFile = "${homeDir}/.claude/channels/discord/access.json";

  mergeDiscordChannelAccessCommand = "${pkgs.python312}/bin/python3 ${../../scripts/merge-discord-channel-access.py}";

  bridgePythonEnvironment = pkgs.python312.withPackages (pythonPackages: [
    pythonPackages.discordpy
  ]);

  discordBridgeCommandFor =
    {
      name,
      agent,
      workspaceDirectory,
      oneShotTurnCommand,
    }:
    let
      tokenFile = lib.escapeShellArg "${secretsDirectory}/${toString agent.channel.discord.botTokenSecretName}";
      hasToken = agent.channel.discord.botTokenSecretName != null;
      waitForTokenPrefix = lib.optionalString hasToken "${waitForSecretScript} ${tokenFile} && ";
      tokenAssignment = lib.optionalString hasToken "DISCORD_BOT_TOKEN=$(cat ${tokenFile}) ";
      bridgeArguments = lib.concatStringsSep " " [
        "--agent-name ${lib.escapeShellArg name}"
        "--one-shot-turn-command ${lib.escapeShellArg oneShotTurnCommand}"
        "--workspace-directory ${lib.escapeShellArg workspaceDirectory}"
        "--state-directory ${lib.escapeShellArg (discordChannelEnvDirectoryFor name)}"
      ];
    in
    "${waitForTokenPrefix}${tokenAssignment}PYTHONPATH=${./scripts} exec ${bridgePythonEnvironment}/bin/python3 ${./scripts/bridge.py} ${bridgeArguments}";
in
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options.channel.discord = lib.mkOption {
          type = lib.types.submodule {
            options.botTokenSecretName = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "Name of the decrypted secret file in ~/.secrets/ that holds the Discord bot token.";
            };
            options.allowedChannelsSecretName = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "Name of the decrypted secret file in ~/.secrets/ holding the Discord channel snowflakes this agent is allowed to respond in, merged into the agent's own access.json under groups.";
            };
          };
          default = { };
          description = "Discord adapter-specific options. Used only when channel.type = 'discord'.";
        };
      }
    );
  };

  config = {
    clawde.channelAdapters.discord = {
      instructions = discordAdapterInstructions;
      launchFlags = _: "--channels plugin:discord@claude-plugins-official";
      environmentSetterFor =
        { name, agent }:
        let
          stateDirectoryAssignment = "DISCORD_STATE_DIR=${lib.escapeShellArg (discordChannelEnvDirectoryFor name)} ";
          tokenFile = lib.escapeShellArg "${secretsDirectory}/${toString agent.channel.discord.botTokenSecretName}";
          hasToken = agent.channel.discord.botTokenSecretName != null;
          waitForTokenPrefix = lib.optionalString hasToken "${waitForSecretScript} ${tokenFile} && ";
          tokenAssignment = lib.optionalString hasToken "DISCORD_BOT_TOKEN=$(cat ${tokenFile}) ";
        in
        "${waitForTokenPrefix}${stateDirectoryAssignment}${tokenAssignment}";
      workspaceSettingsFor = _: {
        hooks.Stop = [
          {
            hooks = [
              {
                type = "command";
                command = "${enforceDiscordReplyStopHook}";
              }
            ];
          }
        ];
        enabledPlugins."discord@claude-plugins-official" = true;
      };

      sidecarWindowSpecificationsFor =
        {
          name,
          agent,
          workspaceDirectory,
          oneShotTurnCommand,
        }:
        lib.optionals (oneShotTurnCommand != null) [
          {
            name = "${name}-discord";
            wrapper_command = discordBridgeCommandFor {
              inherit
                name
                agent
                workspaceDirectory
                oneShotTurnCommand
                ;
            };
          }
        ];

      agentActivationScriptFor =
        {
          name,
          agent,
          ...
        }:
        let
          secretInjectionLine =
            if agent.channel.discord.botTokenSecretName != null then
              "${injectOneSecretScript} ${lib.escapeShellArg "${secretsDirectory}/${agent.channel.discord.botTokenSecretName}"} ${lib.escapeShellArg (discordChannelEnvDirectoryFor name)} DISCORD_BOT_TOKEN"
            else
              "";
          channelsSecretFlag =
            lib.optionalString (agent.channel.discord.allowedChannelsSecretName != null)
              " --channels-secret-file ${lib.escapeShellArg "${secretsDirectory}/${agent.channel.discord.allowedChannelsSecretName}"}";
          mergeChannelAccessLine = "${mergeDiscordChannelAccessCommand} --state-directory ${lib.escapeShellArg (discordChannelEnvDirectoryFor name)} --shared-access-file ${lib.escapeShellArg sharedDiscordAccessFile}${channelsSecretFlag}";
        in
        ''
          ${secretInjectionLine}
          ${mergeChannelAccessLine}
        '';
      preActivation = if hasDiscordAgents then "run ${updateClaudePluginsMarketplace}" else null;
    };
  };
}
