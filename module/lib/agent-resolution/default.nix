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

  eligibleHarnesses = import ./eligible-harnesses.nix {
    inherit lib cfg;
    inherit (effectiveAgent) effectiveAgentForHarnessName;
  };
in
registries // effectiveAgent // eligibleHarnesses
