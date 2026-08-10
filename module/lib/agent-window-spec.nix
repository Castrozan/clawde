{
  pkgs,
  lib,
  effectiveAgentByName,
  effectiveAgentForHarnessName,
  eligibleHarnessNamesFor,
  resolveAgentTypeInstructions,
  clawdeRuntimeInstructions,
  a2aPeerHelpers,
  agentWorkspaceDirectory,
  agentInstructionsFile,
  agentLaunchConfigFile,
  resolveChannelAdapterInstructions,
  resolveChannelAdapterLaunchFlag,
  resolveChannelAdapterEnvironmentSetter,
  getChannelAdapterFor,
  getHarnessFor,
  serializeHarnessRuntimeProfile,
  sidecarProcessLogFile,
}:
let
  sessionArgvShellExpansion = "\${CLAWDE_SESSION_ARGV:-}";

  buildAgentInstructionsContent = agent: ''
    ${agent.personality}

    ${clawdeRuntimeInstructions}

    ${resolveAgentTypeInstructions agent}

    ${resolveChannelAdapterInstructions agent}

    ${a2aPeerHelpers.instructionsBlockForAgent agent}

    ${agent.additionalInstructions}
  '';

  buildAgentInstructionsContentByName =
    name: buildAgentInstructionsContent (effectiveAgentByName name);

  buildAgentLaunchCommand =
    name: agent:
    let
      workspaceDirectory = agentWorkspaceDirectory name;
      environmentSetter = resolveChannelAdapterEnvironmentSetter name agent;
      harness = getHarnessFor agent;
      harnessLaunchCommand =
        if agent.launchOnTrigger then
          harness.buildRunOnceCommandFor {
            inherit name agent workspaceDirectory;
            instructionsFile = agentInstructionsFile name;
          }
        else
          harness.buildLaunchCommandFor {
            inherit name agent workspaceDirectory;
            instructionsFile = agentInstructionsFile name;
            channelLaunchFlags = resolveChannelAdapterLaunchFlag agent;
            inherit sessionArgvShellExpansion;
          };
    in
    "cd ${workspaceDirectory} && ${environmentSetter}${harnessLaunchCommand}";

  launchConfig = import ./agent-launch-config.nix {
    inherit
      pkgs
      lib
      effectiveAgentByName
      effectiveAgentForHarnessName
      eligibleHarnessNamesFor
      getHarnessFor
      serializeHarnessRuntimeProfile
      agentWorkspaceDirectory
      agentInstructionsFile
      agentLaunchConfigFile
      buildAgentLaunchCommand
      ;
  };

  buildAgentWindowCommand =
    name: _agent:
    let
      workspaceDirectory = agentWorkspaceDirectory name;
      execPythonWrapperInvocation = lib.concatStringsSep " " [
        "exec"
        "env"
        "PYTHONPATH=${../scripts/agent-wrapper}:${../scripts/harness}"
        "${pkgs.python312}/bin/python3"
        "${../scripts/agent-wrapper}/wrapper.py"
        "--agent-name ${lib.escapeShellArg name}"
        "--config-file ${lib.escapeShellArg (agentLaunchConfigFile name)}"
      ];
    in
    pkgs.writeShellScript "clawde-agent-${name}" ''
      mkdir -p ${lib.escapeShellArg workspaceDirectory}
      cd ${lib.escapeShellArg workspaceDirectory}
      ${execPythonWrapperInvocation}
    '';

  channelSidecarProcessesForAgent =
    name: agent:
    let
      adapter = getChannelAdapterFor agent;
      workspaceDirectory = agentWorkspaceDirectory name;
    in
    if adapter == null then
      [ ]
    else
      map (sidecar: sidecar // { log_file = sidecarProcessLogFile sidecar.name; }) (
        adapter.sidecarProcessSpecificationsFor {
          inherit name agent workspaceDirectory;
          launchConfigPath = agentLaunchConfigFile name;
        }
      );

  buildAgentSpecification = name: agent: {
    inherit name;
    wrapper_command = "exec ${buildAgentWindowCommand name agent}";
    sidecar_processes = channelSidecarProcessesForAgent name agent;
  };

  buildSpecificationForOneAgent = name: buildAgentSpecification name (effectiveAgentByName name);
in
{
  inherit
    buildSpecificationForOneAgent
    buildAgentInstructionsContentByName
    ;
  inherit (launchConfig) buildAgentLaunchConfigByName;
}
