{ lib, ... }:
{
  options.clawde.channelAdapters = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule (
        { config, ... }:
        {
          options = {
            instructions = lib.mkOption {
              type = lib.types.lines;
              default = "";
              description = "Markdown block concatenated into the agent CLAUDE.md after the base clawde-runtime block when an agent picks this channel.type.";
            };
            instructionsFor = lib.mkOption {
              type = lib.types.functionTo lib.types.lines;
              default = _: config.instructions;
              description = "Function: agent -> the instruction block for exactly this agent, overriding instructions when the transport this agent resolved onto needs a different reply contract (a bridged sidecar agent returns plain assistant text for the bridge to post, an embedded agent replies through the channel plugin's tool).";
            };
            launchFlags = lib.mkOption {
              type = lib.types.functionTo lib.types.str;
              default = _: "";
              description = "Function: agent -> shell string of extra flags appended to the claude command line.";
            };
            environmentSetterFor = lib.mkOption {
              type = lib.types.functionTo lib.types.str;
              default = _: "";
              description = "Function: { name, agent } -> shell prefix that exports any env vars the adapter needs in the agent's launch command (e.g., DISCORD_BOT_TOKEN=$(cat ...), DISCORD_STATE_DIR=...).";
            };
            workspaceDirectoryFor = lib.mkOption {
              type = lib.types.functionTo (lib.types.nullOr lib.types.str);
              default = _: null;
              description = "Function: agent -> absolute workspace path, or null to fall back to the clawde default (~/clawde/<name>).";
            };
            workspaceSettingsFor = lib.mkOption {
              type = lib.types.functionTo (lib.types.attrsOf lib.types.anything);
              default = _: { };
              description = "Function: { name, agent } -> harness-native settings this adapter needs, merged by the harness into the agent's own per-agent settings file (hooks that enforce a reply, plugin enablement, and the like). Expressed in the vocabulary of the harnesses this adapter declares support for.";
            };
            agentActivationScriptFor = lib.mkOption {
              type = lib.types.functionTo lib.types.str;
              default = _: "";
              description = "Function: { name, agent, workspaceDirectory, harnessBinary } -> shell snippet appended to home.activation. Used for adapter-specific workspace seeding (secret injection, channel access files, and the like).";
            };
            sidecarProcessSpecificationsFor = lib.mkOption {
              type = lib.types.functionTo (lib.types.listOf (lib.types.attrsOf lib.types.anything));
              default = _: [ ];
              description = "Function: { name, agent, workspaceDirectory, oneShotTurnCommand } -> headless processes this adapter needs running beside the agent, each { name, command, process_match_pattern }. Used when the harness carries no inbound transport of its own and the channel has to be bridged by a separate process. The supervisor owns these directly rather than giving them a multiplexer window, so the agent's own window stays the single entrypoint a human opens, and their output goes to a log file instead of a pane. process_match_pattern must identify exactly this agent's process in a `pgrep -f` over the whole machine, so it has to carry a delimiter after the agent name or it matches every agent whose name starts with this one. oneShotTurnCommand is null when the harness has no headless mode, which is the adapter's signal to emit nothing.";
            };
            preActivation = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "Optional activation snippet run once when at least one agent uses this adapter (e.g., marketplace pull, plugin install).";
            };
          };
        }
      )
    );
    default = { };
    description = "Channel adapter implementations. Each module that wants to provide a new agent.channel.type registers itself here.";
  };
}
