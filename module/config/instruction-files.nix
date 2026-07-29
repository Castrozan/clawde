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
    agentNames
    runtimeLocations
    buildAgentInstructionsContentByName
    ;

  agentInstructionsFiles = lib.listToAttrs (
    map (name: {
      name = runtimeLocations.agentInstructionsRelativeToHome name;
      value = {
        text = buildAgentInstructionsContentByName name;
      };
    }) agentNames
  );
in
{
  config = lib.mkIf hasAgents {
    home.file = agentInstructionsFiles;
  };
}
