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

  buildHeartbeatDriverArgv =
    name: agent:
    [
      "${pkgs.python312}/bin/python3"
      "${../scripts/heartbeat}/driver.py"
      "--session"
      agent.tmuxSession
      "--window"
      name
      "--launch-config"
      (agentLaunchConfigFile name)
      "--interval"
      agent.heartbeatInterval
      "--prompt"
      agent.heartbeatPrompt
    ]
    ++ lib.optionals (agent.heartbeatGateCommand != null) [
      "--gate-command"
      agent.heartbeatGateCommand
    ];

  launchCommandByHarnessName =
    name:
    lib.genAttrs (eligibleHarnessNamesFor name) (
      harnessName: buildAgentLaunchCommand name (effectiveAgentForHarnessName name harnessName)
    );

  runtimeProfileByHarnessName =
    name:
    lib.genAttrs (eligibleHarnessNamesFor name) (
      harnessName:
      serializeHarnessRuntimeProfile harnessName (getHarnessFor (
        effectiveAgentForHarnessName name harnessName
      )).runtimeProfile
    );

  buildAgentLaunchConfig = name: agent: {
    declared_harness = agent.harness;
    harness_fallback_chain = agent.harnessFallbackChain;
    harness_launch_commands = launchCommandByHarnessName name;
    harness_runtime_profiles = runtimeProfileByHarnessName name;
    heartbeat_driver_argv =
      if (!agent.launchOnTrigger && agent.heartbeatInterval != null) then
        buildHeartbeatDriverArgv name agent
      else
        null;
    launch_gate_command = if agent.launchOnTrigger then agent.heartbeatGateCommand else null;
    launch_gate_interval_seconds =
      if agent.launchOnTrigger then agent.launchGateIntervalSeconds else null;
    active_hours_start = agent.activeHoursStart;
    active_hours_end = agent.activeHoursEnd;
    active_weekdays_only = agent.activeWeekdaysOnly;
    daily_session_rotation = agent.dailySessionRotation;
    on_demand = agent.onDemand;
    idle_timeout_minutes = agent.idleTimeoutMinutes;
    workspace_directory = agentWorkspaceDirectory name;
    tmux_session = agent.tmuxSession;
  };

  buildAgentLaunchConfigByName = name: buildAgentLaunchConfig name (effectiveAgentByName name);

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
      inherit (getHarnessFor agent) buildOneShotTurnCommandFor;
      workspaceDirectory = agentWorkspaceDirectory name;
    in
    if adapter == null then
      [ ]
    else
      map (sidecar: sidecar // { log_file = sidecarProcessLogFile sidecar.name; }) (
        adapter.sidecarProcessSpecificationsFor {
          inherit name agent workspaceDirectory;
          oneShotTurnCommand =
            if buildOneShotTurnCommandFor == null then
              null
            else
              buildOneShotTurnCommandFor {
                inherit name agent workspaceDirectory;
                instructionsFile = agentInstructionsFile name;
              };
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
    buildAgentLaunchConfigByName
    ;
}
