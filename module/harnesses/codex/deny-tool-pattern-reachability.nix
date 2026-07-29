{ lib }:
let
  registeredMcpServerNamesFor =
    agent:
    if agent.mcpConfigFile == null then
      [ ]
    else
      builtins.attrNames ((builtins.fromJSON (builtins.readFile agent.mcpConfigFile)).mcpServers or { });

  namesAnUnregisteredMcpServer =
    agent: pattern:
    let
      captures = builtins.match "mcp__(.*)__\\*" pattern;
    in
    captures != null && !(builtins.elem (builtins.head captures) (registeredMcpServerNamesFor agent));

  namesASkillInvocation = pattern: builtins.match "Skill\\(.*\\)" pattern != null;
in
{
  unenforceableDenyToolPatternsFor =
    { agent, denyToolPatterns, ... }:
    builtins.filter (
      pattern: !(namesASkillInvocation pattern || namesAnUnregisteredMcpServer agent pattern)
    ) denyToolPatterns;

  inherit registeredMcpServerNamesFor;
}
