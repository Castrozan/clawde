{
  config,
  lib,
  pkgs,
  ...
}:
let
  helpers = import ../lib/lib.nix { inherit pkgs config lib; };
  inherit (helpers)
    hasAgents
    homeDir
    agentNames
    agentWorkspaceDirectory
    effectiveAgentByName
    getHarnessFor
    getChannelAdapterFor
    ;

  workspaceRelativeToHome = name: lib.removePrefix "${homeDir}/" (agentWorkspaceDirectory name);

  resolveChannelWorkspaceSettings =
    name: agent:
    let
      adapter = getChannelAdapterFor agent;
    in
    if adapter != null then adapter.workspaceSettingsFor { inherit name agent; } else { };

  harnessWorkspaceFiles =
    name:
    let
      agent = effectiveAgentByName name;
    in
    (getHarnessFor agent).workspaceFilesFor {
      inherit name agent;
      workspaceDirectory = agentWorkspaceDirectory name;
      workspaceRelativeToHome = workspaceRelativeToHome name;
      channelWorkspaceSettings = resolveChannelWorkspaceSettings name agent;
    };

  allAgentWorkspaceFiles = lib.foldl' (
    accumulated: name: accumulated // harnessWorkspaceFiles name
  ) { } agentNames;
in
{
  config = lib.mkIf hasAgents {
    home.file = allAgentWorkspaceFiles;
  };
}
