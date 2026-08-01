{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options.expose = lib.mkOption {
          type = lib.types.submodule {
            options = {
              a2a = lib.mkOption {
                type = lib.types.submodule {
                  options = {
                    agentDescriptionForCard = lib.mkOption {
                      type = lib.types.str;
                      default = "";
                      description = "Free-form description published in this agent's A2A card. Every agent pane is reachable whether or not anything is set here; this only replaces the generated 'harness session <name>' line with something a caller can route on. Empty keeps the generated one.";
                    };
                    meaningfulLinePattern = lib.mkOption {
                      type = lib.types.nullOr lib.types.str;
                      default = null;
                      description = "Regex matching the only pane lines that count as this agent's answer. Filters out status-line and spinner redraws so a task's output carries the reply rather than the chrome around it. Null inherits the harness's own response-marker pattern, which is the right answer unless the agent renders through something else.";
                    };
                  };
                };
                default = { };
                description = "How this agent presents itself to the A2A daemon that serves every agent pane on the machine.";
              };
            };
          };
          default = { };
          description = "Interop adapters that expose this agent to non-channel consumers (other agents, scripts, services).";
        };
      }
    );
  };
}
