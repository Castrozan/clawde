{
  lib,
  ...
}:
{
  options.clawde.agents = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule {
        options = {
          heartbeatInterval = lib.mkOption {
            type = lib.types.nullOr lib.types.str;
            default = null;
            description = "Cron expression. When set, the agent runs an autonomous polling loop. Null inherits the agent type's default.";
          };
          heartbeatPrompt = lib.mkOption {
            type = lib.types.nullOr lib.types.str;
            default = null;
            description = "Prompt sent on each heartbeat tick. Required when the effective heartbeatInterval is set. Null inherits the agent type's default.";
          };
          heartbeatGateCommand = lib.mkOption {
            type = lib.types.nullOr lib.types.str;
            default = null;
            description = "Shell command run before each heartbeat tick. Exit 0 fires the tick and wakes the LLM; any non-zero exit skips the tick without spending tokens. Null inherits the agent type's default, then always fires. Only meaningful when heartbeatInterval is set.";
          };
          activeHoursStart = lib.mkOption {
            type = lib.types.nullOr lib.types.int;
            default = null;
            description = "Hour (0-23) when agent becomes active. Null inherits the agent type's default, then 24/7.";
          };
          activeHoursEnd = lib.mkOption {
            type = lib.types.nullOr lib.types.int;
            default = null;
            description = "Hour (0-23) when agent goes dormant. Null inherits the agent type's default.";
          };
          activeWeekdaysOnly = lib.mkOption {
            type = lib.types.nullOr lib.types.bool;
            default = null;
            description = "When true the agent stays dormant on Saturday and Sunday, active only Monday-Friday within its active-hours window. Null inherits the agent type's default, then false (runs every day).";
          };
          dailySessionRotation = lib.mkOption {
            type = lib.types.nullOr lib.types.bool;
            default = null;
            description = "Kill and restart the harness process once per day to prevent context accumulation. Null inherits the agent type's default, then false.";
          };
          launchOnTrigger = lib.mkOption {
            type = lib.types.nullOr lib.types.bool;
            default = null;
            description = "When true the agent keeps no warm session: instead of a persistent harness process prodded by the heartbeat driver, the wrapper evaluates the heartbeat gate command on an interval and launches a single run-once cycle only when the gate fires, then goes dormant until the next trigger. Reuses heartbeatGateCommand as the launch gate and heartbeatPrompt as the run-once prompt. Null inherits the agent type's default, then false.";
          };
          launchGateIntervalSeconds = lib.mkOption {
            type = lib.types.nullOr lib.types.int;
            default = null;
            description = "Seconds between launch-gate checks when launchOnTrigger is set. Null inherits the agent type's default, then 900.";
          };
          onDemand = lib.mkOption {
            type = lib.types.nullOr lib.types.bool;
            default = null;
            description = "When true the supervisor never brings the agent up on its own: it stays fully stopped, holding no process and no multiplexer window, until an operator runs `clawde start <agent>`. The agent then runs a normal warm session until it has been idle for idleTimeoutMinutes, at which point the supervisor tears it down again. Its session record survives the teardown, so the next start resumes the same conversation. Null inherits the agent type's default, then false.";
          };
          idleTimeoutMinutes = lib.mkOption {
            type = lib.types.nullOr lib.types.int;
            default = null;
            description = "Minutes of conversation silence after which an onDemand agent stops itself. Measured from the session transcript's last write, floored at the moment the operator started the agent so a fresh start is never immediately idle. Null inherits the agent type's default, then 30.";
          };
        };
      }
    );
  };
}
