{
  config,
  lib,
  pkgs,
  ...
}:
let
  helpers = import ../lib/lib.nix { inherit pkgs config lib; };
  inherit (helpers)
    hasAgents
    homeDir
    defaultTmuxSessionName
    clawdeRuntimePaths
    clawdeServiceSpecification
    clawdeServiceSpecificationFile
    ;

  clawdeServiceScript = "${../scripts/clawde-service}/clawde-service.py";

  clawdeSessionStarter = pkgs.writeShellScriptBin "clawde" ''
    export PYTHONPATH=${clawdePythonModuleSearchPath}
    case "''${1:-}" in
      active)
        shift
        exec ${pkgs.python312}/bin/python3 ${../scripts/agent-wrapper}/activate_after_hours.py "$@"
        ;;
      list)
        shift
        exec ${pkgs.python312}/bin/python3 ${../scripts/agent-wrapper}/list_agents.py "$@"
        ;;
      harness)
        shift
        exec ${pkgs.python312}/bin/python3 ${../scripts/agent-wrapper}/harness_control.py "$@"
        ;;
      start|stop)
        exec ${pkgs.python312}/bin/python3 ${../scripts/agent-wrapper}/on_demand_control.py "$@"
        ;;
    esac
    export TMUX_BIN=${pkgs.tmux}/bin/tmux
    export DEFAULT_TMUX_SESSION_NAME=${lib.escapeShellArg defaultTmuxSessionName}
    export SYSTEMD_USER_SERVICE_NAME=clawde
    export LAUNCHD_LABEL=org.nix-community.home.clawde
    ${builtins.readFile ../scripts/start-clawde.sh}
  '';

  clawdeGracefulRedeployScript = ../scripts/clawde-redeploy.py;

  clawdePythonModuleSearchPath = "${../scripts/agent-wrapper}:${../scripts/harness}";
  clawdeResumeNudgeScript = "${../scripts/heartbeat}/resume_nudge.py";

  clawdeHeartbeatChangeGate = pkgs.writeShellScriptBin "clawde-heartbeat-change-gate" ''
    exec ${pkgs.python312}/bin/python3 ${../scripts/heartbeat}/change_gate.py "$@"
  '';

  clawdeGracefulRedeploy = pkgs.writeShellScriptBin "clawde-redeploy" ''
    export CLAWDE_RESUME_NUDGE_SCRIPT=${clawdeResumeNudgeScript}
    export CLAWDE_HEARTBEAT_SCRIPTS_DIR=${../scripts/heartbeat}
    export PYTHONPATH=${clawdePythonModuleSearchPath}
    exec ${pkgs.python312}/bin/python3 ${clawdeGracefulRedeployScript} "$@"
  '';

  clawdeServiceExecArguments = [
    "${pkgs.python312}/bin/python3"
    "${clawdeServiceScript}"
    "--specification-file"
    "${clawdeServiceSpecificationFile}"
  ];

  linuxSystemdUnit = {
    Unit = {
      Description = "clawde persistent agents supervisor";
      After = [
        "network.target"
        "agenix.service"
      ];
      Wants = [ "agenix.service" ];
      StartLimitBurst = 5;
      StartLimitIntervalSec = 300;
      X-RestartIfChanged = false;
    };
    Service = {
      Type = "simple";
      ExecStart = lib.concatStringsSep " " clawdeServiceExecArguments;
      Restart = "always";
      RestartSec = "10s";
      KillMode = "process";
      Environment = [
        "PATH=${clawdeRuntimePaths}"
        "HOME=${homeDir}"
        "TMUX_TMPDIR=%t"
        "XDG_RUNTIME_DIR=%t"
        "CLAWDE_MULTIPLEXER=${config.clawde.multiplexer}"
        "PYTHONPATH=${clawdePythonModuleSearchPath}"
      ];
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };

  darwinLaunchdAgent = {
    enable = true;
    config = {
      ProgramArguments = clawdeServiceExecArguments;
      KeepAlive = true;
      RunAtLoad = true;
      ThrottleInterval = 10;
      EnvironmentVariables = {
        PATH = clawdeRuntimePaths;
        HOME = homeDir;
        CLAWDE_MULTIPLEXER = config.clawde.multiplexer;
        PYTHONPATH = clawdePythonModuleSearchPath;
      };
      StandardOutPath = "${homeDir}/Library/Logs/clawde.out.log";
      StandardErrorPath = "${homeDir}/Library/Logs/clawde.err.log";
    };
  };
in
{
  options.clawde.serviceSpecification = lib.mkOption {
    type = lib.types.attrs;
    readOnly = true;
    default = clawdeServiceSpecification;
    description = "Every supervised window the clawde service owns, agents and their sidecars alike, as the data the supervisor is handed. Exposed so a configuration can assert over what will actually be brought up rather than over the options it set, without forcing the specification file to build.";
  };

  config = lib.mkIf hasAgents {
    home.packages = [
      clawdeSessionStarter
      clawdeGracefulRedeploy
      clawdeHeartbeatChangeGate
    ];

    xdg.dataFile."bash-completion/completions/clawde".source = ../scripts/completion/clawde.bash;

    systemd.user.services = lib.mkIf pkgs.stdenv.hostPlatform.isLinux {
      clawde = linuxSystemdUnit;
    };

    launchd.agents = lib.mkIf pkgs.stdenv.hostPlatform.isDarwin {
      clawde = darwinLaunchdAgent;
    };
  };
}
