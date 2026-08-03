{
  config,
  lib,
  pkgs,
  ...
}:
let
  helpers = import ../lib/lib.nix { inherit pkgs config lib; };
in
{
  config = lib.mkIf helpers.hasAgents {
    assertions =
      let
        knownChannelTypes = [ "none" ] ++ builtins.attrNames helpers.cfg.channelAdapters;
        knownAgentTypes = builtins.attrNames helpers.cfg.agentTypes;
        knownHarnesses = builtins.attrNames helpers.cfg.harnesses;
        assertionsForAgent =
          name:
          let
            agent = helpers.cfg.agents.${name};
            effectiveAgent = helpers.effectiveAgentByName name;
            typeDefinition = helpers.cfg.agentTypes.${agent.type} or null;
            harnessDefinition = helpers.getHarnessFor agent;
            unenforceableDenyToolPatterns =
              if harnessDefinition == null then
                [ ]
              else
                harnessDefinition.unenforceableDenyToolPatternsFor {
                  inherit name;
                  agent = effectiveAgent;
                  inherit (effectiveAgent) denyToolPatterns;
                };
            missingRequiredParams =
              if typeDefinition == null then
                [ ]
              else
                builtins.filter (
                  param: (agent.typeParams.${agent.type}.${param} or null) == null
                ) typeDefinition.requiredParams;
            discordTransportResolution =
              if agent.channel.type == "discord" then
                (import ../lib/discord-transport.nix { inherit lib; }).resolve
                  effectiveAgent.channel.discord.transport
                  harnessDefinition
              else
                null;
          in
          [
            {
              assertion = effectiveAgent.personality != null;
              message = "Agent ${name}: personality is required - set it on the instance or supply a personality template on type '${agent.type}'.";
            }
            {
              assertion = (effectiveAgent.activeHoursStart == null) == (effectiveAgent.activeHoursEnd == null);
              message = "Agent ${name}: activeHoursStart and activeHoursEnd must both be set or both be null.";
            }
            {
              assertion = builtins.elem agent.channel.type knownChannelTypes;
              message = "Agent ${name}: channel.type must be one of ${lib.concatStringsSep ", " knownChannelTypes} (got '${agent.channel.type}').";
            }
            {
              assertion =
                !(
                  agent.mcpServers != null
                  && agent.channel.type == "discord"
                  && discordTransportResolution != null
                  && discordTransportResolution.transport == "embedded"
                );
              message = "Agent ${name}: mcpServers is incompatible with an embedded discord channel, because channel.discord.transport resolved to 'embedded' for harness '${agent.harness}'. An agent-scoped MCP set launches the harness in strict MCP mode, so it loads only the servers named there and excludes the discord plugin's own MCP server, which makes the channel silently fail to connect. Drop mcpServers on embedded channel agents and scope their tools with denyToolPatterns instead, or set channel.discord.transport = 'sidecar' so the bridge carries the channel and the harness can run strict MCP.";
            }
            {
              assertion = builtins.elem agent.type knownAgentTypes;
              message = "Agent ${name}: type must be one of ${lib.concatStringsSep ", " knownAgentTypes} (got '${agent.type}').";
            }
            {
              assertion = missingRequiredParams == [ ];
              message = "Agent ${name}: type '${agent.type}' requires typeParams.${agent.type} fields ${lib.concatStringsSep ", " missingRequiredParams} to be set and non-null.";
            }
            {
              assertion = builtins.elem agent.harness knownHarnesses;
              message = "Agent ${name}: harness must be one of ${lib.concatStringsSep ", " knownHarnesses} (got '${agent.harness}').";
            }
            {
              assertion =
                harnessDefinition == null
                || builtins.elem agent.channel.type harnessDefinition.supportedChannelTypes;
              message = "Agent ${name}: harness '${agent.harness}' cannot transport channel.type '${agent.channel.type}'; it serves ${
                lib.concatStringsSep ", " (harnessDefinition.supportedChannelTypes or [ ])
              }. Move the agent to a harness that carries this channel, or drop the channel.";
            }
            {
              assertion = discordTransportResolution == null || discordTransportResolution.satisfiable;
              message = "Agent ${name}: channel.discord.transport = '${effectiveAgent.channel.discord.transport}' is not satisfiable on harness '${agent.harness}'. The harness embeds discord for ${
                lib.concatStringsSep ", " (harnessDefinition.embeddedChannelTypes or [ ])
              } and its headless one-shot turn command is ${
                if harnessDefinition.buildOneShotTurnCommandFor == null then "absent" else "present"
              }; set the transport to a value the harness can serve, or move the agent to another harness.";
            }
            {
              assertion = unenforceableDenyToolPatterns == [ ];
              message = "Agent ${name}: harness '${agent.harness}' can neither refuse ${lib.concatStringsSep ", " unenforceableDenyToolPatterns} at call time nor make it unreachable by construction, so moving the agent here would silently drop those guardrails and let it run unrestricted. Keep it on a harness that enforces them, or drop the patterns deliberately.";
            }
          ];
      in
      lib.concatMap assertionsForAgent helpers.agentNames;
  };
}
