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
}:
let
  claudeResolvedFromAgentRuntimePathForRebuildStability = "claude";

  buildAgentClaudeMarkdownContent = agent: ''
    ${agent.personality}

    ${clawdeRuntimeInstructions}

    ${resolveAgentTypeInstructions agent}

    ${resolveChannelAdapterInstructions agent}

    ${a2aPeerHelpers.instructionsBlockForAgent agent}

    ${agent.additionalInstructions}
  '';

  buildAgentClaudeMarkdownContentByName =
    name: buildAgentClaudeMarkdownContent (effectiveAgentByName name);

  buildAgentLaunchCommand =
    name: agent:
    let
      workspace = agentWorkspaceDirectory name;
      environmentSetter = resolveChannelAdapterEnvironmentSetter name agent;
      channelFlag = resolveChannelAdapterLaunchFlag agent;
      modelFlag = "--model ${agent.model}";
      nameFlag = "--name ${name}";
      permissionModeFlag = "--permission-mode ${agent.permissionMode}";
      skillDirFlags = lib.concatMapStringsSep " " (dir: "--add-dir ${dir}") agent.skillDirectories;
      appendSystemPromptFlag = "--append-system-prompt \"$(cat ${agentInstructionsFile name})\"";
      mcpConfigFlag = lib.optionalString (
        agent.mcpConfigFile != null
      ) "--strict-mcp-config --mcp-config ${agent.mcpConfigFile} ";
    in
    "cd ${workspace} && ${environmentSetter}${claudeResolvedFromAgentRuntimePathForRebuildStability} \${CLAWDE_RESUME_FLAG:-} ${channelFlag} ${modelFlag} ${nameFlag} ${permissionModeFlag} ${mcpConfigFlag}${appendSystemPromptFlag} ${skillDirFlags}";

  buildHeartbeatDriverArgv =
    name: agent:
    [
      "${pkgs.python312}/bin/python3"
      "${../scripts/heartbeat}/driver.py"
      "--session"
      agent.tmuxSession
      "--window"
      name
      "--interval"
      agent.heartbeatInterval
      "--prompt"
      agent.heartbeatPrompt
    ]
    ++ lib.optionals (agent.heartbeatGateCommand != null) [
      "--gate-command"
      agent.heartbeatGateCommand
    ];

  buildAgentLaunchConfig = name: agent: {
    launch_command = buildAgentLaunchCommand name agent;
    heartbeat_driver_argv =
      if agent.heartbeatInterval != null then buildHeartbeatDriverArgv name agent else null;
    active_hours_start = agent.activeHoursStart;
    active_hours_end = agent.activeHoursEnd;
    active_weekdays_only = agent.activeWeekdaysOnly;
    daily_session_rotation = agent.dailySessionRotation;
    tmux_session = agent.tmuxSession;
  };

  buildAgentLaunchConfigByName = name: buildAgentLaunchConfig name (effectiveAgentByName name);

  buildAgentWindowCommand =
    name: _agent:
    let
      workspaceDirectory = agentWorkspaceDirectory name;
      execPythonWrapperInvocation = lib.concatStringsSep " " [
        "exec"
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
      mainSpec = buildAgentSpecification name agent;
      peerSpecs = a2aPeerHelpers.peerWindowSpecificationsForAgent name agent;
    in
    [ mainSpec ] ++ peerSpecs;
in
{
  inherit
    buildAllSpecificationsForOneAgent
    buildAgentClaudeMarkdownContentByName
    buildAgentLaunchConfigByName
    ;
}
