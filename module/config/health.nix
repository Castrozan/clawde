{
  config,
  lib,
  pkgs,
  healthCheckLib ? null,
  ...
}:
let
  agentWrapperDirectory = ../scripts/agent-wrapper;
  sharedHarnessDirectory = ../scripts/harness;
  agentPaneResponsivenessCheckerScript = "${agentWrapperDirectory}/check_agent_pane_responsiveness.py";
  agentExpectedRunningCheckerScript = "${agentWrapperDirectory}/agent_expected_running.py";

  agentExpectedRunningCommand =
    agentName:
    lib.concatStringsSep " " [
      "PYTHONPATH=${lib.escapeShellArg "${agentWrapperDirectory}:${sharedHarnessDirectory}"}"
      "${pkgs.python312}/bin/python3"
      agentExpectedRunningCheckerScript
      "--agent-name"
      (lib.escapeShellArg agentName)
    ];

  runtimeLocations = import ../lib/runtime-locations.nix {
    homeDir = config.home.homeDirectory;
  };

  clawdeAgentProcessProbes = lib.mapAttrsToList (
    agentName: _agentConfig:
    healthCheckLib.mkProcessProbe {
      name = "clawde agent: ${agentName}";
      pattern = "agent-wrapper/wrapper.py --agent-name ${agentName}";
      applicableWhen = agentExpectedRunningCommand agentName;
    }
  ) config.clawde.agents;

  clawdeAgentPaneLivenessProbes = lib.mapAttrsToList (
    agentName: agentConfig:
    healthCheckLib.mkCommandProbe {
      name = "clawde agent pane responsiveness: ${agentName}";
      applicableWhen = agentExpectedRunningCommand agentName;
      command = lib.concatStringsSep " " [
        "PYTHONPATH=${lib.escapeShellArg "${agentWrapperDirectory}:${sharedHarnessDirectory}"}"
        "${pkgs.python312}/bin/python3"
        "${agentPaneResponsivenessCheckerScript}"
        "--tmux-target"
        (lib.escapeShellArg "${agentConfig.tmuxSession}:${agentName}")
        "--launch-config"
        (lib.escapeShellArg (runtimeLocations.agentLaunchConfigFile agentName))
      ];
    }
  ) config.clawde.agents;

  clawdeAgentProbes = clawdeAgentProcessProbes ++ clawdeAgentPaneLivenessProbes;

  clawdeServiceProbe =
    if pkgs.stdenv.hostPlatform.isDarwin then
      healthCheckLib.mkLaunchdProbe {
        name = "clawde service (launchd)";
        label = "org.nix-community.home.clawde";
      }
    else
      healthCheckLib.mkSystemdUserUnitProbe {
        name = "clawde service (systemd)";
        unit = "clawde.service";
      };

  clawdeServiceEnabled = (lib.length clawdeAgentProbes) > 0;
in
lib.mkIf (healthCheckLib != null) {
  healthCheck.probes = clawdeAgentProbes ++ lib.optional clawdeServiceEnabled clawdeServiceProbe;
}
