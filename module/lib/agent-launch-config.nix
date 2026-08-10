{
  pkgs,
  lib,
  effectiveAgentByName,
  effectiveAgentForHarnessName,
  eligibleHarnessNamesFor,
  getHarnessFor,
  serializeHarnessRuntimeProfile,
  agentWorkspaceDirectory,
  agentInstructionsFile,
  agentLaunchConfigFile,
  buildAgentLaunchCommand,
}:
let
  buildHeartbeatDriverArgv =
    name: agent:
    [
      "${pkgs.coreutils}/bin/env"
      "PYTHONPATH=${../scripts/agent-wrapper}:${../scripts/harness}"
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

  oneShotTurnCommandByHarnessName =
    name:
    lib.genAttrs (eligibleHarnessNamesFor name) (
      harnessName:
      let
        agentOnHarness = effectiveAgentForHarnessName name harnessName;
        harness = getHarnessFor agentOnHarness;
      in
      if harness.buildOneShotTurnCommandFor == null then
        null
      else
        harness.buildOneShotTurnCommandFor {
          inherit name;
          agent = agentOnHarness;
          workspaceDirectory = agentWorkspaceDirectory name;
          instructionsFile = agentInstructionsFile name;
        }
    );

  buildAgentLaunchConfig = name: agent: {
    declared_harness = agent.harness;
    harness_fallback_chain = agent.harnessFallbackChain;
    harness_launch_commands = launchCommandByHarnessName name;
    harness_runtime_profiles = runtimeProfileByHarnessName name;
    harness_one_shot_turn_commands = oneShotTurnCommandByHarnessName name;
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
in
{
  inherit buildAgentLaunchConfigByName;
}
