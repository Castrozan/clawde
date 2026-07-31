{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          workspaceDirectory = lib.mkOption {
            type = lib.types.nullOr lib.types.str;
            default = null;
            description = "Override the agent's workspace path. When null, the agent type then the active channel adapter decides (and falls back to ~/clawde/<name>).";
          };

          tmuxSession = lib.mkOption {
            type = lib.types.str;
            default = "clawde";
            description = "Multiplexer workspace label that hosts this agent's window. Agents sharing the same value live as windows of the same workspace; distinct values create separate ones, all supervised by the single clawde service. Defaults to 'clawde'.";
          };

          channel = lib.mkOption {
            type = lib.types.submodule {
              options.type = lib.mkOption {
                type = lib.types.str;
                default = "none";
                description = "Channel adapter type. 'none' means the agent has no inbound channel and is invoked manually. Any other value must match a registered clawde.channelAdapters entry. Adapters extend this submodule with their own option subkey (e.g., channel.discord, channel.pm).";
              };
            };
            default = { };
            description = "Channel adapter configuration (how the agent receives and sends messages).";
          };
        };
      }
    );
  };
}
