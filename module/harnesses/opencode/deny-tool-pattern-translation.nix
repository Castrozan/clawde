let
  bashCommandCaptured = pattern: builtins.match "Bash\\((.*)\\)" pattern;

  mcpServerCaptured = pattern: builtins.match "mcp__(.*)__\\*" pattern;

  skillInvocationCaptured = pattern: builtins.match "Skill\\((.*)\\)" pattern;

  registeredMcpServerNames =
    agent: if agent.mcpServers == null then [ ] else builtins.attrNames agent.mcpServers;

  namesAnUnregisteredMcpServer =
    agent: pattern:
    let
      captures = mcpServerCaptured pattern;
    in
    captures != null && !(builtins.elem (builtins.head captures) (registeredMcpServerNames agent));

  claudeBashPatternAsOpencodeCommandPattern =
    claudePattern:
    let
      colonSeparated = builtins.match "([^:]*):\\*" claudePattern;
    in
    if colonSeparated != null then "${builtins.head colonSeparated} *" else claudePattern;

  deniedBashCommandPatterns =
    denyToolPatterns:
    let
      captured = builtins.filter (capture: capture != null) (map bashCommandCaptured denyToolPatterns);
    in
    map (capture: claudeBashPatternAsOpencodeCommandPattern (builtins.head capture)) captured;

  deniedSkillNames =
    denyToolPatterns:
    let
      captured = builtins.filter (capture: capture != null) (
        map skillInvocationCaptured denyToolPatterns
      );
    in
    map builtins.head captured;
in
{
  bashPermissionRuleFor =
    denyToolPatterns:
    let
      deniedCommandPatterns = deniedBashCommandPatterns denyToolPatterns;
    in
    if deniedCommandPatterns == [ ] then
      "allow"
    else
      builtins.listToAttrs (
        map (commandPattern: {
          name = commandPattern;
          value = "deny";
        }) deniedCommandPatterns
      )
      // {
        "*" = "allow";
      };

  skillPermissionRuleFor =
    denyToolPatterns:
    let
      deniedNames = deniedSkillNames denyToolPatterns;
    in
    if deniedNames == [ ] then
      "allow"
    else
      builtins.listToAttrs (
        map (skillName: {
          name = skillName;
          value = "deny";
        }) deniedNames
      )
      // {
        "*" = "allow";
      };

  unenforceableDenyToolPatternsFor =
    { agent, denyToolPatterns, ... }:
    builtins.filter (
      pattern:
      !(
        bashCommandCaptured pattern != null
        || skillInvocationCaptured pattern != null
        || namesAnUnregisteredMcpServer agent pattern
      )
    ) denyToolPatterns;
}
