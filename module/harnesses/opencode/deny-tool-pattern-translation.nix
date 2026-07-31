let
  bashCommandCaptured = pattern: builtins.match "Bash\\((.*)\\)" pattern;

  mcpServerCaptured = pattern: builtins.match "mcp__(.*)__\\*" pattern;

  skillInvocationCaptured = pattern: builtins.match "Skill\\((.*)\\)" pattern;

  opencodePermissionKeyByClaudeToolName = {
    Edit = "edit";
    Write = "edit";
    NotebookEdit = "edit";
    Read = "read";
    Glob = "glob";
    Grep = "grep";
    Task = "task";
    TodoWrite = "todowrite";
    WebFetch = "webfetch";
    WebSearch = "websearch";
  };

  permissionKeyDeniedByBareToolName =
    pattern: opencodePermissionKeyByClaudeToolName.${pattern} or null;

  alwaysAllowedPermissionKeys = [
    "read"
    "edit"
    "glob"
    "grep"
    "list"
    "task"
    "lsp"
    "external_directory"
    "todowrite"
    "webfetch"
    "websearch"
    "doom_loop"
    "question"
  ];

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

  capturedValues =
    capture: denyToolPatterns:
    map builtins.head (builtins.filter (captures: captures != null) (map capture denyToolPatterns));

  deniedBashCommandPatterns =
    denyToolPatterns:
    map claudeBashPatternAsOpencodeCommandPattern (capturedValues bashCommandCaptured denyToolPatterns);

  deniedPermissionKeys =
    denyToolPatterns:
    builtins.filter (key: key != null) (map permissionKeyDeniedByBareToolName denyToolPatterns);

  denyEverythingNamedRule =
    deniedNames:
    if deniedNames == [ ] then
      "allow"
    else
      builtins.listToAttrs (
        map (deniedName: {
          name = deniedName;
          value = "deny";
        }) deniedNames
      )
      // {
        "*" = "allow";
      };
in
{
  permissionMapFor =
    agent:
    let
      deniedKeys = deniedPermissionKeys agent.denyToolPatterns;
      actionForKey = key: if builtins.elem key deniedKeys then "deny" else "allow";
    in
    builtins.listToAttrs (
      map (key: {
        name = key;
        value = actionForKey key;
      }) alwaysAllowedPermissionKeys
    )
    // {
      bash = denyEverythingNamedRule (deniedBashCommandPatterns agent.denyToolPatterns);
      skill = denyEverythingNamedRule (capturedValues skillInvocationCaptured agent.denyToolPatterns);
    };

  unenforceableDenyToolPatternsFor =
    { agent, denyToolPatterns, ... }:
    builtins.filter (
      pattern:
      !(
        bashCommandCaptured pattern != null
        || skillInvocationCaptured pattern != null
        || permissionKeyDeniedByBareToolName pattern != null
        || namesAnUnregisteredMcpServer agent pattern
      )
    ) denyToolPatterns;
}
