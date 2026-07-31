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
    cfg
    agentWorkspaceDirectory
    effectiveAgentByName
    effectiveAgentForHarnessName
    eligibleHarnessNamesFor
    getChannelAdapterFor
    ;

  workspaceRelativeToHome = name: lib.removePrefix "${homeDir}/" (agentWorkspaceDirectory name);

  resolveChannelWorkspaceSettings =
    name: agent:
    let
      adapter = getChannelAdapterFor agent;
    in
    if adapter != null then adapter.workspaceSettingsFor { inherit name agent; } else { };

  workspaceFilesOnHarness =
    name: harnessName:
    let
      agent = effectiveAgentForHarnessName name harnessName;
    in
    cfg.harnesses.${harnessName}.workspaceFilesFor {
      inherit name agent;
      workspaceDirectory = agentWorkspaceDirectory name;
      workspaceRelativeToHome = workspaceRelativeToHome name;
      channelWorkspaceSettings = resolveChannelWorkspaceSettings name (effectiveAgentByName name);
    };

  harnessWorkspaceFiles =
    name:
    lib.foldl' (accumulated: harnessName: accumulated // workspaceFilesOnHarness name harnessName) { } (
      eligibleHarnessNamesFor name
    );

  allAgentWorkspaceFiles = lib.foldl' (
    accumulated: name: accumulated // harnessWorkspaceFiles name
  ) { } agentNames;
in
{
  config = lib.mkIf hasAgents {
    home.file = allAgentWorkspaceFiles;
  };
}
