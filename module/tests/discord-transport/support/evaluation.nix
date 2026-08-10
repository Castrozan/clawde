{
  pkgs,
  lib,
  module,
}:
let
  stubHomeModule = {
    options = {
      home = {
        username = lib.mkOption {
          type = lib.types.str;
          default = "fixture-user";
        };
        homeDirectory = lib.mkOption {
          type = lib.types.str;
          default = "/home/fixture-user";
        };
        file = lib.mkOption {
          type = lib.types.attrsOf lib.types.anything;
          default = { };
        };
        packages = lib.mkOption {
          type = lib.types.listOf lib.types.package;
          default = [ ];
        };
        activation = lib.mkOption {
          type = lib.types.attrsOf lib.types.anything;
          default = { };
        };
      };
      xdg.dataFile = lib.mkOption {
        type = lib.types.attrsOf lib.types.anything;
        default = { };
      };
      systemd.user.services = lib.mkOption {
        type = lib.types.attrsOf lib.types.anything;
        default = { };
      };
      launchd.agents = lib.mkOption {
        type = lib.types.attrsOf lib.types.anything;
        default = { };
      };
      healthCheck.probes = lib.mkOption {
        type = lib.types.listOf lib.types.anything;
        default = [ ];
      };
      assertions = lib.mkOption {
        type = lib.types.listOf (
          lib.types.submodule {
            options = {
              assertion = lib.mkOption {
                type = lib.types.bool;
              };
              message = lib.mkOption {
                type = lib.types.str;
              };
            };
          }
        );
        default = [ ];
      };
    };
  };

  discordAgentConfig =
    {
      harness,
      transport,
      lifetime,
      dailySessionRotation ? false,
      mcpServers ? null,
    }:
    {
      type = "generic";
      personality = "fixture agent";
      inherit harness;
      inherit dailySessionRotation;
      channel.type = "discord";
      channel.discord = {
        inherit transport;
        sidecarLifetime = lifetime;
        botTokenSecretName = "fixture-discord-token";
      };
      inherit mcpServers;
    };

  evaluatedFor =
    agentConfig:
    lib.evalModules {
      modules = [
        {
          _module.args = {
            inherit pkgs;
            healthCheckLib = null;
            lib = lib // {
              hm = {
                dag = {
                  entryAfter = _name: value: value;
                  entryBefore = _name: value: value;
                };
              };
            };
            hostname = "fixture-host";
          };
        }
        stubHomeModule
        module
        {
          clawde = {
            multiplexer = "herdr";
            agents.fixture-agent = agentConfig;
            harnesses = {
              claude.package = pkgs.hello;
              codex.package = pkgs.hello;
              opencode.package = pkgs.hello;
            };
          };
        }
      ];
    };

  homeFileTextFor =
    evaluated: relativePath:
    let
      fileEntry = evaluated.config.home.file.${relativePath};
    in
    fileEntry.text or (throw "no text at ${relativePath}");

  launchConfigTextFor =
    evaluated: homeFileTextFor evaluated "clawde/launch-config/fixture-agent.json";
  commandValueWithin =
    harnessName: blockText:
    let
      matched = builtins.match (''.*"'' + harnessName + ''":"(([^"\\]|\\.)*)".*'') blockText;
    in
    if matched == null then "" else builtins.head matched;

  commandValueFor =
    key: nextKey: evaluated: harnessName:
    let
      block = builtins.match (''.*"'' + key + ''":(.*),"'' + nextKey + ''":.*'') (
        launchConfigTextFor evaluated
      );
    in
    if block == null then "" else commandValueWithin harnessName (builtins.head block);

  harnessLaunchCommandFor =
    evaluated: harnessName:
    commandValueFor "harness_launch_commands" "harness_one_shot_turn_commands" evaluated harnessName;

  oneShotTurnCommandFor =
    evaluated: harnessName:
    commandValueFor "harness_one_shot_turn_commands" "harness_runtime_profiles" evaluated harnessName;

  settingsTextFor =
    evaluated:
    let
      settingsPath = "clawde/fixture-agent/.claude/settings.json";
    in
    if evaluated.config.home.file ? ${settingsPath} then
      evaluated.config.home.file.${settingsPath}.text
    else
      "";

  instructionsFor = evaluated: homeFileTextFor evaluated "clawde/instructions/fixture-agent.md";

  sidecarProcessesFor =
    evaluated:
    (builtins.elemAt (builtins.elemAt evaluated.config.clawde.serviceSpecification.sessions 0).agents 0)
    .sidecar_processes;
in
{
  inherit
    evaluatedFor
    discordAgentConfig
    harnessLaunchCommandFor
    oneShotTurnCommandFor
    settingsTextFor
    instructionsFor
    sidecarProcessesFor
    ;
}
