{
  pkgs,
  lib,
}:
let
  a2aPeerAdapterInstructions = builtins.readFile ./instructions/a2a-peer-runtime.md;

  repoAgentsDirectory = ./.;
in
{
  instructionsBlockForAgent = _agent: a2aPeerAdapterInstructions;

  fleetDaemonExecArguments =
    {
      listenHost,
      listenPort,
      agentMetadataFile,
    }:
    [
      "${pkgs.python312}/bin/python3"
      "-m"
      "a2a_server"
      "--listen-host"
      listenHost
      "--listen-port"
      (toString listenPort)
      "--agent-metadata-file"
      "${agentMetadataFile}"
    ];

  fleetDaemonPythonModuleSearchPath = "${repoAgentsDirectory}";

  buildAgentMetadataDocument = agents: harnessMeaningfulLinePatterns: {
    inherit harnessMeaningfulLinePatterns;
    agents = lib.mapAttrs (_: agent: {
      description = agent.expose.a2a.agentDescriptionForCard;
      inherit (agent.expose.a2a) meaningfulLinePattern;
    }) agents;
  };
}
