{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          harness = lib.mkOption {
            type = lib.types.str;
            default = "claude";
            description = "Agent CLI this agent runs on. Selects a registered clawde.harnesses entry that owns the launch command, the pane markers the runtime reads, session resume, and the harness's own per-agent configuration files.";
          };
          model = lib.mkOption {
            type = lib.types.nullOr lib.types.str;
            default = null;
            description = "Model identifier in the harness's own vocabulary (claude aliases like opus/sonnet, codex ids like gpt-5.6-sol, opencode provider/model pairs). Applies only to the declared harness, since a model name from one harness is meaningless to another. Null inherits the agent type's default, falling back to the harness's defaultModel.";
          };
          modelByHarness = lib.mkOption {
            type = lib.types.attrsOf lib.types.str;
            default = { };
            description = "Model identifier per harness name, consulted before `model`. Pins what the agent runs on after `clawde harness <agent> <harness>` moves it to a harness other than the declared one; harnesses left unnamed here fall back to the agent type's default for that harness, then to the harness's own defaultModel.";
          };
          reasoningEffort = lib.mkOption {
            type = lib.types.str;
            default = "high";
            description = "Reasoning effort for harnesses that expose it as a dial separate from the model. Ignored by harnesses that fold effort into the model identifier.";
          };
          permissionMode = lib.mkOption {
            type = lib.types.nullOr (
              lib.types.enum [
                "default"
                "acceptEdits"
                "plan"
                "bypassPermissions"
              ]
            );
            default = null;
            description = "How much the agent may do without asking. Null inherits the agent type's default, falling back to 'default'. 'bypassPermissions' for fully autonomous agents. Harnesses that model this differently translate the value; codex and opencode agents are unattended by construction and ignore it.";
          };
        };
      }
    );
  };
}
