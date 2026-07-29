{
  cfg,
  getAgentTypeFor,
  getHarnessFor,
}:
let
  firstNonNull = preferred: fallback: if preferred != null then preferred else fallback;
in
{
  effectiveAgentByName =
    name:
    let
      agent = cfg.agents.${name};
      agentType = getAgentTypeFor agent;
      harness = getHarnessFor agent;
      harnessDefaultModel = if harness != null then harness.defaultModel else null;
      typeDefault = selector: if agentType != null then selector agentType else null;
      typeList = selector: if agentType != null then selector agentType else [ ];
      typePersonality = if agentType != null then agentType.personalityTemplateFor agent else null;
    in
    agent
    // {
      model = firstNonNull agent.model (
        firstNonNull (typeDefault (t: t.defaultModelByHarness.${agent.harness} or null)) harnessDefaultModel
      );
      permissionMode = firstNonNull agent.permissionMode (
        firstNonNull (typeDefault (t: t.defaultPermissionMode)) "default"
      );
      dailySessionRotation = firstNonNull agent.dailySessionRotation (
        firstNonNull (typeDefault (t: t.defaultDailySessionRotation)) false
      );
      launchOnTrigger = firstNonNull agent.launchOnTrigger (
        firstNonNull (typeDefault (t: t.defaultLaunchOnTrigger)) false
      );
      launchGateIntervalSeconds = firstNonNull agent.launchGateIntervalSeconds (
        firstNonNull (typeDefault (t: t.defaultLaunchGateIntervalSeconds)) 900
      );
      onDemand = firstNonNull agent.onDemand (firstNonNull (typeDefault (t: t.defaultOnDemand)) false);
      idleTimeoutMinutes = firstNonNull agent.idleTimeoutMinutes (
        firstNonNull (typeDefault (t: t.defaultIdleTimeoutMinutes)) 30
      );
      personality = firstNonNull agent.personality typePersonality;
      heartbeatInterval = firstNonNull agent.heartbeatInterval (
        typeDefault (t: t.defaultHeartbeatInterval)
      );
      heartbeatPrompt = firstNonNull agent.heartbeatPrompt (typeDefault (t: t.defaultHeartbeatPrompt));
      heartbeatGateCommand = firstNonNull agent.heartbeatGateCommand (
        typeDefault (t: t.defaultHeartbeatGateCommand)
      );
      activeHoursStart = firstNonNull agent.activeHoursStart (typeDefault (t: t.defaultActiveHoursStart));
      activeHoursEnd = firstNonNull agent.activeHoursEnd (typeDefault (t: t.defaultActiveHoursEnd));
      activeWeekdaysOnly = firstNonNull agent.activeWeekdaysOnly (
        firstNonNull (typeDefault (t: t.defaultActiveWeekdaysOnly)) false
      );
      denyToolPatterns = (typeList (t: t.defaultDenyToolPatterns)) ++ agent.denyToolPatterns;
      skillDirectories = agent.skillDirectories ++ (typeList (t: t.defaultSkillDirectories));
    };
}
