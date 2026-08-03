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
  hasEmbeddedDiscordAgents = lib.any (
    name: discordTransportForAgent cfg.agents.${name} == "embedded"
  ) (builtins.attrNames agentsUsingDiscord);

  discordTransportResolution = import ../../lib/discord-transport.nix { inherit lib; };

  discordAdapterInstructions = builtins.readFile ./instructions/discord-runtime.md;
  discordSidecarAdapterInstructions = builtins.readFile ./instructions/discord-runtime-sidecar.md;

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

  discordBridgeIdentifyingArgumentsFor =
    name: "--agent-name ${lib.escapeShellArg name} --one-shot-turn-command";

  discordBridgeProcessMatchPatternFor =
    name: "bridge.py ${discordBridgeIdentifyingArgumentsFor name}";

  discordTransportForAgent =
    agent:
    (discordTransportResolution.resolve agent.channel.discord.transport (
      config.clawde.harnesses.${agent.harness} or null
    )).transport;

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
      rotationFlag = lib.optionalString agent.dailySessionRotation "--daily-session-rotation";
      bridgeArguments = lib.concatStringsSep " " [
        "${./scripts/bridge.py} ${discordBridgeIdentifyingArgumentsFor name} ${lib.escapeShellArg oneShotTurnCommand}"
        "--workspace-directory ${lib.escapeShellArg workspaceDirectory}"
        "--state-directory ${lib.escapeShellArg (discordChannelEnvDirectoryFor name)}"
        rotationFlag
      ];
    in
    "${waitForTokenPrefix}${tokenAssignment}PYTHONPATH=${./scripts} exec ${bridgePythonEnvironment}/bin/python3 ${bridgeArguments}";
in
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options.channel.discord = lib.mkOption {
          type = lib.types.submodule {
            options = {
              botTokenSecretName = lib.mkOption {
                type = lib.types.nullOr lib.types.str;
                default = null;
                description = "Name of the decrypted secret file in ~/.secrets/ that holds the Discord bot token.";
              };
              allowedChannelsSecretName = lib.mkOption {
                type = lib.types.nullOr lib.types.str;
                default = null;
                description = "Name of the decrypted secret file in ~/.secrets/ holding the Discord channel snowflakes this agent is allowed to respond in, merged into the agent's own access.json under groups.";
              };
              transport = lib.mkOption {
                type = lib.types.enum [
                  "auto"
                  "embedded"
                  "sidecar"
                ];
                default = "auto";
                description = "How the Discord channel is carried for this agent. 'auto' embeds when the harness serves discord in-process (claude plugin) and bridges through the sidecar one-shot turn otherwise (codex, opencode). 'embedded' forces the in-process plugin and 'sidecar' forces the bridge; forcing a transport the harness cannot provide fails a build-time assertion. Exactly one Discord client exists per bot token: a sidecar agent never also launches the plugin.";
              };
              sidecarLifetime = lib.mkOption {
                type = lib.types.enum [
                  "agent"
                  "service"
                ];
                default = "agent";
                description = "How long the sidecar bridge stays supervised. 'agent' follows the agent's own run decision: it stops whenever onDemand, launch gates, active hours, or idle teardown keep the wrapper absent. 'service' keeps the bridge connected whenever the agent is declared, so the agent can be woken per message even while its window is dormant.";
              };
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

      instructionsFor =
        agent:
        if discordTransportForAgent agent == "sidecar" then
          discordSidecarAdapterInstructions
        else
          discordAdapterInstructions;

      launchFlags =
        agent:
        lib.optionalString (
          discordTransportForAgent agent == "embedded"
        ) "--channels plugin:discord@claude-plugins-official";

      environmentSetterFor =
        { name, agent }:
        lib.optionalString (discordTransportForAgent agent == "embedded") (
          let
            stateDirectoryAssignment = "DISCORD_STATE_DIR=${lib.escapeShellArg (discordChannelEnvDirectoryFor name)} ";
            tokenFile = lib.escapeShellArg "${secretsDirectory}/${toString agent.channel.discord.botTokenSecretName}";
            hasToken = agent.channel.discord.botTokenSecretName != null;
            waitForTokenPrefix = lib.optionalString hasToken "${waitForSecretScript} ${tokenFile} && ";
            tokenAssignment = lib.optionalString hasToken "DISCORD_BOT_TOKEN=$(cat ${tokenFile}) ";
          in
          "${waitForTokenPrefix}${stateDirectoryAssignment}${tokenAssignment}"
        );

      workspaceSettingsFor =
        { agent, ... }:
        if discordTransportForAgent agent == "embedded" then
          {
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
          }
        else
          { };

      sidecarProcessSpecificationsFor =
        {
          name,
          agent,
          workspaceDirectory,
          oneShotTurnCommand,
        }:
        lib.optionals (oneShotTurnCommand != null) [
          {
            name = "${name}-discord";
            command = discordBridgeCommandFor {
              inherit
                name
                agent
                workspaceDirectory
                oneShotTurnCommand
                ;
            };
            process_match_pattern = discordBridgeProcessMatchPatternFor name;
            enabled = discordTransportForAgent agent == "sidecar";
            lifetime = agent.channel.discord.sidecarLifetime;
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
      preActivation = if hasEmbeddedDiscordAgents then "run ${updateClaudePluginsMarketplace}" else null;
    };
  };
}
