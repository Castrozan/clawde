{
  pkgs,
  lib,
  effectiveAgentByName,
  resolveAgentTypeInstructions,
  clawdeRuntimeInstructions,
  a2aPeerHelpers,
  agentWorkspaceDirectory,
  agentInstructionsFile,
  agentLaunchConfigFile,
  resolveChannelAdapterInstructions,
  resolveChannelAdapterLaunchFlag,
  resolveChannelAdapterEnvironmentSetter,
  getHarnessFor,
  serializeHarnessRuntimeProfile,
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

  buildAgentLaunchConfig =
    name: agent:
    let
      inherit (getHarnessFor agent) runtimeProfile;
    in
    {
      launch_command = buildAgentLaunchCommand name agent;
      harness_runtime_profile = serializeHarnessRuntimeProfile agent.harness runtimeProfile;
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
        "PYTHONPATH=${../scripts/harness}"
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

  buildAgentSpecification = name: agent: {
    inherit name;
    wrapper_command = "exec ${buildAgentWindowCommand name agent}";
  };

  buildAllSpecificationsForOneAgent =
    name:
    let
      agent = effectiveAgentByName name;
      outputLinePattern = (getHarnessFor agent).meaningfulOutputLinePattern;
      mainSpec = buildAgentSpecification name agent;
      peerSpecs = a2aPeerHelpers.peerWindowSpecificationsForAgent name agent outputLinePattern;
    in
    [ mainSpec ] ++ peerSpecs;
in
{
  inherit
    buildAllSpecificationsForOneAgent
    buildAgentInstructionsContentByName
    buildAgentLaunchConfigByName
    ;
}
