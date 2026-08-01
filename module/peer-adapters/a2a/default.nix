{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.clawde;
  helpers = import ../../lib/lib.nix { inherit pkgs config lib; };
  inherit (helpers) hasAgents homeDir clawdeRuntimePaths;

  a2aHelpers = import ./lib.nix { inherit pkgs lib; };

  harnessMeaningfulLinePatterns = lib.mapAttrs (
    _: harness: harness.meaningfulOutputLinePattern
  ) cfg.harnesses;

  agentMetadataDocument = a2aHelpers.buildAgentMetadataDocument cfg.agents harnessMeaningfulLinePatterns;

  agentMetadataFile = pkgs.writeText "clawde-a2a-agent-metadata.json" (
    builtins.toJSON agentMetadataDocument
  );

  fleetDaemonExecArguments = a2aHelpers.fleetDaemonExecArguments {
    inherit (cfg.a2a) listenHost listenPort;
    inherit agentMetadataFile;
  };

  fleetDaemonEnvironment = {
    PATH = clawdeRuntimePaths;
    HOME = homeDir;
    PYTHONPATH = a2aHelpers.fleetDaemonPythonModuleSearchPath;
  };

  linuxSystemdUnit = {
    Unit = {
      Description = "clawde a2a daemon serving every agent pane on this machine";
      After = [ "network.target" ];
      StartLimitBurst = 5;
      StartLimitIntervalSec = 300;
    };
    Service = {
      Type = "simple";
      ExecStart = lib.concatStringsSep " " fleetDaemonExecArguments;
      Restart = "always";
      RestartSec = "10s";
      Environment = lib.mapAttrsToList (name: value: "${name}=${value}") fleetDaemonEnvironment;
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };

  darwinLaunchdAgent = {
    enable = true;
    config = {
      ProgramArguments = fleetDaemonExecArguments;
      KeepAlive = true;
      RunAtLoad = true;
      ThrottleInterval = 10;
      EnvironmentVariables = fleetDaemonEnvironment;
      StandardOutPath = "${homeDir}/Library/Logs/clawde-a2a.out.log";
      StandardErrorPath = "${homeDir}/Library/Logs/clawde-a2a.err.log";
    };
  };
in
{
  options.clawde.a2a = {
    listenHost = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = "Bind host for the A2A daemon. The transport has zero built-in auth and every agent pane on the machine is reachable through it, so binding anywhere but loopback hands any host on the LAN a keyboard into every live session. Front a non-loopback bind with a reverse proxy that authenticates.";
    };
    listenPort = lib.mkOption {
      type = lib.types.int;
      default = 7000;
      description = "Bind port for the A2A daemon. One port serves the whole fleet; each agent is addressed by path under /agents/<name>.";
    };
    agentMetadata = lib.mkOption {
      type = lib.types.attrs;
      readOnly = true;
      default = agentMetadataDocument;
      description = "Descriptions and line-pattern overrides the daemon merges onto the agents it discovers. Exposed as data so a configuration can assert over what the daemon will actually read without forcing the metadata file to build.";
    };
  };

  config = lib.mkIf hasAgents {
    assertions = [
      {
        assertion = cfg.multiplexer == "herdr";
        message = "The A2A daemon discovers agents by asking herdr which panes are running one, so it needs clawde.multiplexer = \"herdr\". On tmux there is no per-pane agent or turn state to discover and the daemon would serve an empty fleet.";
      }
      {
        assertion = cfg.a2a.listenPort > 0 && cfg.a2a.listenPort < 65536;
        message = "clawde.a2a.listenPort must be a valid TCP port (1-65535)";
      }
    ];

    systemd.user.services = lib.mkIf pkgs.stdenv.hostPlatform.isLinux {
      clawde-a2a = linuxSystemdUnit;
    };

    launchd.agents = lib.mkIf pkgs.stdenv.hostPlatform.isDarwin {
      clawde-a2a = darwinLaunchdAgent;
    };
  };
}
