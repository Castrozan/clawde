{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          personality = lib.mkOption {
            type = lib.types.nullOr lib.types.lines;
            default = null;
            description = "Identity, role, personality - the specialization-layer content unique to this agent. Null inherits the agent type's personality template; the effective value must be non-null.";
          };
          additionalInstructions = lib.mkOption {
            type = lib.types.lines;
            default = "";
            description = "Extra instructions concatenated after base + channel adapter blocks. Overlays for further specialization (PM, browser, etc).";
          };
          type = lib.mkOption {
            type = lib.types.str;
            default = "generic";
            description = "Agent type. Selects a registered clawde.agentTypes entry whose defaults (model, heartbeat, personality template, deny patterns, skill directories, packages) are inherited by this agent unless the instance overrides them. 'generic' inherits nothing.";
          };
          typeParams = lib.mkOption {
            type = lib.types.submodule { options = { }; };
            default = { };
            description = "Per-agent parameters consumed by the agent's type. Each agent type re-opens this submodule with its own subkey (e.g., typeParams.project-manager).";
          };
        };
      }
    );
  };
}
