{
  config,
  lib,
  pkgs,
  ...
}:
let
  helpers = import ../lib/lib.nix { inherit pkgs config lib; };
  inherit (helpers)
    cfg
    hasAgents
    agentNames
    agentWorkspaceDirectory
    harnessBinaryFor
    getChannelAdapterFor
    getAgentTypeFor
    effectiveAgentByName
    effectiveAgentForHarnessName
    eligibleHarnessNamesFor
    ;

  eligibleHarnessNamesAcrossAllAgents = lib.unique (lib.concatMap eligibleHarnessNamesFor agentNames);

  perAgentActivationLines =
    resolveProvider: providerSelector:
    lib.concatMapStringsSep "\n" (
      name:
      let
        agent = effectiveAgentByName name;
        provider = resolveProvider agent;
      in
      if provider != null then
        (providerSelector provider) {
          inherit name agent;
          workspaceDirectory = agentWorkspaceDirectory name;
          harnessBinary = harnessBinaryFor agent;
        }
      else
        ""
    ) agentNames;

  runAllChannelAdapterAgentActivations =
    pkgs.writeShellScript "clawde-run-all-channel-adapter-agent-activations"
      (perAgentActivationLines getChannelAdapterFor (provider: provider.agentActivationScriptFor));

  runAllAgentTypeActivations = pkgs.writeShellScript "clawde-run-all-agent-type-activations" (
    perAgentActivationLines getAgentTypeFor (provider: provider.agentActivationScriptFor)
  );

  perEligibleHarnessActivationLines = lib.concatMapStringsSep "\n" (
    name:
    lib.concatMapStringsSep "\n" (
      harnessName:
      let
        agent = effectiveAgentForHarnessName name harnessName;
      in
      cfg.harnesses.${harnessName}.agentActivationScriptFor {
        inherit name agent;
        workspaceDirectory = agentWorkspaceDirectory name;
        harnessBinary = harnessBinaryFor agent;
      }
    ) (eligibleHarnessNamesFor name)
  ) agentNames;

  runAllHarnessAgentActivations = pkgs.writeShellScript "clawde-run-all-harness-agent-activations" perEligibleHarnessActivationLines;

  preActivationLinesFor =
    registry: registeredNames:
    lib.concatMapStringsSep "\n" (
      entryName:
      let
        entry = registry.${entryName};
      in
      if entry.preActivation != null then entry.preActivation else ""
    ) registeredNames;

in
{
  config = lib.mkIf hasAgents {
    home.activation = {
      runChannelAdapterPreActivations = lib.hm.dag.entryAfter [ "writeBoundary" ] (
        preActivationLinesFor cfg.channelAdapters (builtins.attrNames cfg.channelAdapters)
      );

      runAgentTypePreActivations = lib.hm.dag.entryAfter [ "writeBoundary" ] (
        preActivationLinesFor cfg.agentTypes (builtins.attrNames cfg.agentTypes)
      );

      runHarnessPreActivations = lib.hm.dag.entryAfter [ "writeBoundary" ] (
        preActivationLinesFor cfg.harnesses eligibleHarnessNamesAcrossAllAgents
      );

      runChannelAdapterAgentActivations = lib.hm.dag.entryAfter [ "runChannelAdapterPreActivations" ] ''
        run ${runAllChannelAdapterAgentActivations}
      '';

      runAgentTypeActivations = lib.hm.dag.entryAfter [ "runAgentTypePreActivations" ] ''
        run ${runAllAgentTypeActivations}
      '';

      runHarnessAgentActivations = lib.hm.dag.entryAfter [ "runHarnessPreActivations" ] ''
        run ${runAllHarnessAgentActivations}
      '';
    };
  };
}
