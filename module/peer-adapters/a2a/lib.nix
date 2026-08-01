{
  pkgs,
  lib,
  multiplexer,
}:
let
  a2aPeerAdapterInstructions = builtins.readFile ./instructions/a2a-peer-runtime.md;

  repoAgentsDirectory = ./.;

  resolveA2APeerPublicEndpointUrl =
    agent:
    if agent.expose.a2a.publicEndpointUrl != null then
      agent.expose.a2a.publicEndpointUrl
    else
      "http://${agent.expose.a2a.listenHost}:${toString agent.expose.a2a.listenPort}";

  resolveA2APeerCardDescription =
    name: agent:
    if agent.expose.a2a.agentDescriptionForCard != "" then
      agent.expose.a2a.agentDescriptionForCard
    else
      "clawde agent ${name}";

  resolveA2APeerMeaningfulLinePattern =
    agent: harnessMeaningfulOutputLinePattern:
    if agent.expose.a2a.meaningfulLinePattern != null then
      agent.expose.a2a.meaningfulLinePattern
    else
      harnessMeaningfulOutputLinePattern;

  attachmentArgumentsForTheLiveMultiplexer =
    name: agent:
    if multiplexer == "herdr" then
      [
        "--backend-type"
        "herdr"
        "--herdr-workspace-label"
        (lib.escapeShellArg agent.tmuxSession)
        "--herdr-tab-label"
        (lib.escapeShellArg name)
      ]
    else
      [
        "--backend-type"
        "tmux"
        "--tmux-session-name"
        (lib.escapeShellArg agent.tmuxSession)
        "--tmux-window-name"
        (lib.escapeShellArg name)
      ];

  buildA2APeerCommand =
    name: agent: harnessMeaningfulOutputLinePattern:
    pkgs.writeShellScript "clawde-a2a-peer-${name}" (
      lib.concatStringsSep " " (
        [
          "exec"
          "env"
          "PYTHONPATH=${repoAgentsDirectory}"
          "${pkgs.python312}/bin/python3"
          "-m"
          "a2a_server"
          "--agent-name"
          (lib.escapeShellArg name)
          "--agent-description"
          (lib.escapeShellArg (resolveA2APeerCardDescription name agent))
          "--listen-host"
          (lib.escapeShellArg agent.expose.a2a.listenHost)
          "--listen-port"
          (toString agent.expose.a2a.listenPort)
          "--public-endpoint-url"
          (lib.escapeShellArg (resolveA2APeerPublicEndpointUrl agent))
          "--meaningful-line-pattern"
          (lib.escapeShellArg (resolveA2APeerMeaningfulLinePattern agent harnessMeaningfulOutputLinePattern))
        ]
        ++ attachmentArgumentsForTheLiveMultiplexer name agent
      )
    );

  a2aPeerProcessMatchPatternFor = name: "a2a_server --agent-name ${name} --agent-description";

  buildA2APeerSidecarSpecification = name: agent: harnessMeaningfulOutputLinePattern: {
    name = "${name}-a2a";
    command = "${buildA2APeerCommand name agent harnessMeaningfulOutputLinePattern}";
    process_match_pattern = a2aPeerProcessMatchPatternFor name;
  };
in
{
  instructionsBlockForAgent =
    agent: if agent.expose.a2a.enable then a2aPeerAdapterInstructions else "";

  peerSidecarProcessSpecificationsForAgent =
    name: agent: harnessMeaningfulOutputLinePattern:
    lib.optional agent.expose.a2a.enable (
      buildA2APeerSidecarSpecification name agent harnessMeaningfulOutputLinePattern
    );
}
