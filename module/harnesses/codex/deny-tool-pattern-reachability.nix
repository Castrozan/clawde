let
  namesAnUnregisteredMcpServer =
    agent: pattern:
    let
      captures = builtins.match "mcp__(.*)__\\*" pattern;
    in
    captures != null
    && !(builtins.elem (builtins.head captures) (
      if agent.mcpServers == null then [ ] else builtins.attrNames agent.mcpServers
    ));

  namesASkillInvocation = pattern: builtins.match "Skill\\(.*\\)" pattern != null;
in
{
  unenforceableDenyToolPatternsFor =
    { agent, denyToolPatterns, ... }:
    builtins.filter (
      pattern: !(namesASkillInvocation pattern || namesAnUnregisteredMcpServer agent pattern)
    ) denyToolPatterns;
}
