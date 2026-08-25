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

  clawdeServiceRestartCommand =
    if pkgs.stdenv.hostPlatform.isLinux then
      "systemctl --user daemon-reload && systemctl --user restart clawde"
    else
      "launchctl kickstart -k gui/UID/org.nix-community.home.clawde";

  clawdeSessionStarter = pkgs.writeShellScriptBin "clawde" ''
    export PYTHONPATH=${clawdePythonModuleSearchPath}
    export TMUX_BIN=${pkgs.tmux}/bin/tmux
    export DEFAULT_TMUX_SESSION_NAME=${lib.escapeShellArg defaultTmuxSessionName}
    export CLAWDE_AGENT_WRAPPER_DIR=${../scripts/agent-wrapper}
    export CLAWDE_SERVICE_RESTART_COMMAND=${lib.escapeShellArg clawdeServiceRestartCommand}
    exec ${pkgs.python312}/bin/python3 ${../scripts/clawde_cli.py} "$@"
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

  clawdeServiceDeployedCommandFile = pkgs.writeText "clawde-service-deployed-command" (
    lib.concatStringsSep " " clawdeServiceExecArguments
  );

  clawdeSupervisorRefresh = pkgs.writeShellScriptBin "clawde-supervisor-refresh" ''
    exec ${pkgs.python312}/bin/python3 ${../scripts/clawde-supervisor-refresh.py} \
      --deployed-command-file ${clawdeServiceDeployedCommandFile} \
      --restart-command ${lib.escapeShellArg clawdeServiceRestartCommand} "$@"
  '';

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
    description = "Everything the clawde service owns, each agent's window and the headless sidecar processes hanging off it, as the data the supervisor is handed. Exposed so a configuration can assert over what will actually be brought up rather than over the options it set, without forcing the specification file to build.";
  };

  config = lib.mkIf hasAgents {
    home.packages = [
      clawdeSessionStarter
      clawdeGracefulRedeploy
      clawdeHeartbeatChangeGate
      clawdeSupervisorRefresh
    ];

    home.activation.refreshClawdeSupervisorWhenItsCodeChanges =
      lib.hm.dag.entryAfter [ "writeBoundary" ]
        ''
          run ${clawdeSupervisorRefresh}/bin/clawde-supervisor-refresh
        '';

    xdg.dataFile."bash-completion/completions/clawde".source = ../scripts/completion/clawde.bash;

    systemd.user.services = lib.mkIf pkgs.stdenv.hostPlatform.isLinux {
      clawde = linuxSystemdUnit;
    };

    launchd.agents = lib.mkIf pkgs.stdenv.hostPlatform.isDarwin {
      clawde = darwinLaunchdAgent;
    };
  };
}
