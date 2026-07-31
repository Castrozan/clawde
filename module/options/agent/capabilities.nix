{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          skillDirectories = lib.mkOption {
            type = lib.types.listOf lib.types.str;
            default = [ ];
            description = "Absolute paths to skill sets laid out as <dir>/.claude/skills/<skill-name>, the de-facto on-disk skill format. Each harness projects them into its own discovery mechanism. Composed additively with the agent type's default skill directories.";
          };
          denyToolPatterns = lib.mkOption {
            type = lib.types.listOf lib.types.str;
            default = [ ];
            description = "Tool patterns this agent must never invoke, written into whatever per-agent permission surface the harness provides. Composed additively with the agent type's default deny patterns.";
          };
          mcpServers = lib.mkOption {
            type = lib.types.nullOr (lib.types.attrsOf (lib.types.attrsOf lib.types.anything));
            default = null;
            description = "MCP servers scoped to this agent alone, keyed by server name, in the shape the harness expects for one server. Held as data rather than a config file path so every harness serializes it into its own format, and so nothing has to read a store path back during evaluation, which would build another system's derivation on the evaluating host. Null inherits the user-scoped global set. Any attrset puts the harness in strict MCP mode serving exactly these servers, so the empty set is how an agent is given no MCP servers at all rather than all of them.";
          };
        };
      }
    );
  };
}
