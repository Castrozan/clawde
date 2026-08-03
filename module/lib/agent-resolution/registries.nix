{
  lib,
  cfg,
  agentNames,
  agentWorkspacesBaseDirectory,
}:
rec {
  getChannelAdapterFor = agent: cfg.channelAdapters.${agent.channel.type} or null;

  getAgentTypeFor = agent: cfg.agentTypes.${agent.type} or null;

  getHarnessFor = agent: cfg.harnesses.${agent.harness} or null;

  harnessBinaryFor =
    agent:
    let
      harness = getHarnessFor agent;
    in
    if harness != null && harness.package != null then lib.getExe harness.package else null;

  distinctHarnessNamesInUse = lib.unique (map (name: cfg.agents.${name}.harness) agentNames);

  agentNamesOnHarness =
    harnessName: builtins.filter (name: cfg.agents.${name}.harness == harnessName) agentNames;

  agentWorkspaceDirectory =
    name:
    let
      agent = cfg.agents.${name};
      adapter = getChannelAdapterFor agent;
      agentType = getAgentTypeFor agent;
      typeWorkspace = if agentType != null then agentType.workspaceDirectoryFor agent else null;
      adapterWorkspace = if adapter != null then adapter.workspaceDirectoryFor agent else null;
    in
    if agent.workspaceDirectory != null then
      agent.workspaceDirectory
    else if typeWorkspace != null then
      typeWorkspace
    else if adapterWorkspace != null then
      adapterWorkspace
    else
      "${agentWorkspacesBaseDirectory}/${name}";

  resolveChannelAdapterInstructions =
    agent:
    let
      adapter = getChannelAdapterFor agent;
    in
    if adapter != null then adapter.instructionsFor agent else "";

  resolveChannelAdapterLaunchFlag =
    agent:
    let
      adapter = getChannelAdapterFor agent;
    in
    if adapter != null then adapter.launchFlags agent else "";

  resolveChannelAdapterEnvironmentSetter =
    name: agent:
    let
      adapter = getChannelAdapterFor agent;
    in
    if adapter != null then adapter.environmentSetterFor { inherit name agent; } else "";

  resolveAgentTypeInstructions =
    agent:
    let
      agentType = getAgentTypeFor agent;
    in
    if agentType != null then agentType.runtimeInstructions else "";
}
