{
  lib,
  cfg,
  effectiveAgentForHarnessName,
}:
let
  harnessCarriesAgentChannel =
    agent: harness: builtins.elem agent.channel.type harness.supportedChannelTypes;

  harnessEnforcesAgentDenyPatterns =
    name: harnessName: harness:
    let
      agentOnHarness = effectiveAgentForHarnessName name harnessName;
    in
    harness.unenforceableDenyToolPatternsFor {
      inherit name;
      agent = agentOnHarness;
      inherit (agentOnHarness) denyToolPatterns;
    } == [ ];

  harnessCanRunAgent =
    name: harnessName:
    let
      harness = cfg.harnesses.${harnessName};
    in
    harness.package != null
    && harnessCarriesAgentChannel cfg.agents.${name} harness
    && harnessEnforcesAgentDenyPatterns name harnessName harness;
in
{
  eligibleHarnessNamesFor =
    name:
    lib.unique (
      [ cfg.agents.${name}.harness ]
      ++ builtins.filter (harnessCanRunAgent name) (builtins.attrNames cfg.harnesses)
    );
}
