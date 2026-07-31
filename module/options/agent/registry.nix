{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (lib.types.submodule { options = { }; });
    default = { };
    description = "clawde persistent agents, each supervised as one window of its multiplexer workspace. The sibling files in this directory contribute the option groups an agent is made of, and every other registry (agent types, harnesses, channel adapters) re-opens this same submodule to add the options it owns.";
  };
}
