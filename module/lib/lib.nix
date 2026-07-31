{
  pkgs,
  config,
  lib,
}:
let
  inherit (config.home) username homeDirectory;

  homeDir = homeDirectory;

  runtimeLocations = import ./runtime-locations.nix { inherit homeDir; };

  defaultTmuxSessionName = "clawde";
  agentWorkspacesBaseDirectory = runtimeLocations.runtimeRootDirectory;

  cfg = config.clawde;
  agentNames = builtins.attrNames cfg.agents;
  hasAgents = cfg.agents != { };

  clawdeRuntimePaths = import ./runtime-paths.nix {
    inherit
      pkgs
      lib
      username
      homeDir
      ;
  };

  clawdeRuntimeInstructions =
    builtins.readFile ../instructions/clawde-runtime.md
    + "\n"
    + builtins.readFile ../snippets/rebuild.md;

  a2aPeerHelpers = import ../peer-adapters/a2a/lib.nix { inherit pkgs lib; };

  agentResolution = import ./agent-resolution {
    inherit
      lib
      cfg
      agentNames
      agentWorkspacesBaseDirectory
      ;
  };

  inherit (agentResolution)
    getChannelAdapterFor
    getAgentTypeFor
    getHarnessFor
    harnessBinaryFor
    distinctHarnessNamesInUse
    agentNamesOnHarness
    agentWorkspaceDirectory
    effectiveAgentByName
    effectiveAgentForHarnessName
    eligibleHarnessNamesFor
    resolveAgentTypeInstructions
    resolveChannelAdapterInstructions
    resolveChannelAdapterLaunchFlag
    resolveChannelAdapterEnvironmentSetter
    ;

  harnessRuntimeProfileHelpers = import ./harness-runtime-profile.nix { inherit lib; };

  agentWindowSpecHelpers = import ./agent-window-spec.nix {
    inherit
      pkgs
      lib
      effectiveAgentByName
      effectiveAgentForHarnessName
      eligibleHarnessNamesFor
      resolveAgentTypeInstructions
      clawdeRuntimeInstructions
      a2aPeerHelpers
      agentWorkspaceDirectory
      resolveChannelAdapterInstructions
      resolveChannelAdapterLaunchFlag
      resolveChannelAdapterEnvironmentSetter
      getChannelAdapterFor
      getHarnessFor
      ;
    inherit (harnessRuntimeProfileHelpers) serializeHarnessRuntimeProfile;
    inherit (runtimeLocations) agentInstructionsFile agentLaunchConfigFile sidecarProcessLogFile;
  };
  inherit (agentWindowSpecHelpers)
    buildAllSpecificationsForOneAgent
    buildAgentInstructionsContentByName
    buildAgentLaunchConfigByName
    ;

  distinctTmuxSessionNames = lib.unique (map (name: cfg.agents.${name}.tmuxSession) agentNames);

  agentNamesInTmuxSession =
    sessionName: builtins.filter (name: cfg.agents.${name}.tmuxSession == sessionName) agentNames;

  buildSessionSpecification = sessionName: {
    name = sessionName;
    agents = lib.concatMap buildAllSpecificationsForOneAgent (agentNamesInTmuxSession sessionName);
  };

  clawdeServiceSpecification = {
    sessions = map buildSessionSpecification distinctTmuxSessionNames;
  };

  clawdeServiceSpecificationFile = pkgs.writeText "clawde-service-specification.json" (
    builtins.toJSON clawdeServiceSpecification
  );
in
{
  inherit
    homeDir
    defaultTmuxSessionName
    distinctTmuxSessionNames
    agentWorkspacesBaseDirectory
    cfg
    agentNames
    hasAgents
    clawdeRuntimePaths
    agentWorkspaceDirectory
    getChannelAdapterFor
    getAgentTypeFor
    getHarnessFor
    harnessBinaryFor
    distinctHarnessNamesInUse
    agentNamesOnHarness
    effectiveAgentByName
    effectiveAgentForHarnessName
    eligibleHarnessNamesFor
    clawdeServiceSpecification
    clawdeServiceSpecificationFile
    buildAgentInstructionsContentByName
    buildAgentLaunchConfigByName
    runtimeLocations
    ;
}
