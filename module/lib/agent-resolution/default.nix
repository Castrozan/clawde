{
  lib,
  cfg,
  agentNames,
  agentWorkspacesBaseDirectory,
}:
let
  registries = import ./registries.nix {
    inherit
      lib
      cfg
      agentNames
      agentWorkspacesBaseDirectory
      ;
  };

  effectiveAgent = import ./effective-agent.nix {
    inherit cfg;
    inherit (registries) getAgentTypeFor getHarnessFor;
  };
in
registries // effectiveAgent
