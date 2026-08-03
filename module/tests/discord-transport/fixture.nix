{
  pkgs,
  lib,
  module,
}:
let
  transportResolution = import ../../lib/discord-transport.nix { inherit lib; };

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
          clawde.agents.fixture-agent = agentConfig;
          clawde.harnesses.claude.package = pkgs.hello;
          clawde.harnesses.codex.package = pkgs.hello;
          clawde.harnesses.opencode.package = pkgs.hello;
        }
      ];
    };

  homeFileTextFor =
    evaluated: relativePath:
    let
      fileEntry = evaluated.config.home.file.${relativePath};
    in
    if fileEntry ? text then fileEntry.text else throw "no text at ${relativePath}";

  launchConfigTextFor =
    evaluated: homeFileTextFor evaluated "clawde/launch-config/fixture-agent.json";

  harnessLaunchCommandFor =
    evaluated: harnessName:
    let
      matched = builtins.match (''.*"'' + harnessName + ''":"(([^"\\]|\\.)*)".*'') (
        launchConfigTextFor evaluated
      );
    in
    if matched == null then "" else builtins.head matched;

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

  stringify =
    value:
    if value == null then
      "null"
    else if builtins.isBool value then
      (if value then "true" else "false")
    else
      toString value;

  assertion = name: expected: actual: {
    inherit name expected actual;
  };

  assertContains =
    name: expectedFragment: actual:
    assertion name "contains ${expectedFragment}" (
      if builtins.isString actual && builtins.match ".*${expectedFragment}.*" actual != null then
        "contains ${expectedFragment}"
      else
        actual
    );

  assertLacks =
    name: forbiddenFragment: actual:
    assertion name "lacks ${forbiddenFragment}" (
      if builtins.isString actual && builtins.match ".*${forbiddenFragment}.*" actual == null then
        "lacks ${forbiddenFragment}"
      else
        actual
    );

  claudeAutoEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "auto";
    lifetime = "agent";
  });

  claudeSidecarEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "sidecar";
    lifetime = "agent";
  });

  claudeSidecarServiceLifetimeEvaluated = evaluatedFor (discordAgentConfig {
    harness = "claude";
    transport = "sidecar";
    lifetime = "service";
    dailySessionRotation = true;
  });

  codexSidecarEvaluated = evaluatedFor (discordAgentConfig {
    harness = "codex";
    transport = "auto";
    lifetime = "agent";
  });

  claudeAutoSidecarProcess = builtins.head (sidecarProcessesFor claudeAutoEvaluated);
  claudeSidecarProcess = builtins.head (sidecarProcessesFor claudeSidecarEvaluated);
  claudeSidecarServiceLifetimeProcess = builtins.head (
    sidecarProcessesFor claudeSidecarServiceLifetimeEvaluated
  );
  codexSidecarProcess = builtins.head (sidecarProcessesFor codexSidecarEvaluated);

  claudeSidecarLaunchCommand = harnessLaunchCommandFor claudeSidecarEvaluated "claude";
  claudeAutoLaunchCommand = harnessLaunchCommandFor claudeAutoEvaluated "claude";
  codexLaunchCommand = harnessLaunchCommandFor codexSidecarEvaluated "codex";

  fakeEmbeddingHarness = {
    embeddedChannelTypes = [
      "none"
      "discord"
    ];
    buildOneShotTurnCommandFor = null;
  };
  fakeBridgingHarness = {
    embeddedChannelTypes = [ "none" ];
    buildOneShotTurnCommandFor = "true";
  };
  fakePassiveHarness = {
    embeddedChannelTypes = [ "none" ];
    buildOneShotTurnCommandFor = null;
  };

  transportAssertion =
    name: expected: selected: harness:
    assertion name expected ((transportResolution.resolve selected harness).transport);
in
{
  inherit
    claudeAutoEvaluated
    claudeSidecarEvaluated
    claudeSidecarServiceLifetimeEvaluated
    codexSidecarEvaluated
    ;

  assertions = [
    (assertion "auto-claude-resolves-embedded" "embedded" (
      (transportResolution.resolve "auto" fakeEmbeddingHarness).transport
    ))
    (transportAssertion "auto-codex-resolves-sidecar" "sidecar" "auto" fakeBridgingHarness)
    (transportAssertion "forced-sidecar-on-embedding-harness" "none" "sidecar" fakeEmbeddingHarness)
    (transportAssertion "forced-embedded-on-bridging-harness" "none" "embedded" fakeBridgingHarness)
    (assertion "sidecar-on-passive-harness-unsatisfiable" "false" (
      stringify (transportResolution.resolve "sidecar" fakePassiveHarness).satisfiable
    ))
    (assertion "embedded-on-bridging-harness-unsatisfiable" "false" (
      stringify (transportResolution.resolve "embedded" fakeBridgingHarness).satisfiable
    ))
    (assertion "auto-on-passive-harness-unsatisfiable" "false" (
      stringify (transportResolution.resolve "auto" fakePassiveHarness).satisfiable
    ))
    (assertion "auto-claude-sidecar-enabled" "false" (stringify claudeAutoSidecarProcess.enabled))
    (assertion "auto-claude-sidecar-lifetime" "agent" claudeAutoSidecarProcess.lifetime)
    (assertion "auto-claude-keeps-plugin-launch-flags" "true" (
      stringify (
        builtins.match ".*--channels plugin:discord@claude-plugins-official.*" claudeAutoLaunchCommand
        != null
      )
    ))
    (assertion "auto-claude-keeps-token-environment" "true" (
      stringify (builtins.match ".*DISCORD_BOT_TOKEN.*" claudeAutoLaunchCommand != null)
    ))
    (assertContains "auto-claude-keeps-plugin-workspace-settings" "discord@claude-plugins-official" (
      settingsTextFor claudeAutoEvaluated
    ))
    (assertContains "auto-claude-keeps-reply-stop-hook" "enforce-discord-reply-stop-hook" (
      settingsTextFor claudeAutoEvaluated
    ))
    (assertContains "auto-claude-instructions-use-reply-tool" "reply tool" (
      instructionsFor claudeAutoEvaluated
    ))
    (assertion "claude-sidecar-enabled" "true" (stringify claudeSidecarProcess.enabled))
    (assertion "claude-sidecar-lifetime" "agent" claudeSidecarProcess.lifetime)
    (assertContains "claude-sidecar-command-runs-print-mode" "--print" claudeSidecarProcess.command)
    (assertContains "claude-sidecar-command-carries-session-identifier"
      "CLAWDE_CHANNEL_SESSION_IDENTIFIER"
      claudeSidecarProcess.command
    )
    (assertContains "claude-sidecar-command-resumes-explicitly" "--resume" claudeSidecarProcess.command)
    (assertContains "claude-sidecar-command-starts-fresh-explicitly" "--session-id"
      claudeSidecarProcess.command
    )
    (assertContains "claude-sidecar-command-writes-the-reply-file" "CLAWDE_CHANNEL_REPLY_FILE"
      claudeSidecarProcess.command
    )
    (assertLacks "claude-sidecar-launch-command-drops-plugin-flags"
      "--channels plugin:discord@claude-plugins-official"
      claudeSidecarLaunchCommand
    )
    (assertLacks "claude-sidecar-launch-command-drops-token-environment" "DISCORD_BOT_TOKEN"
      claudeSidecarLaunchCommand
    )
    (assertLacks "claude-sidecar-drops-plugin-workspace-settings" "enabledPlugins" (
      settingsTextFor claudeSidecarEvaluated
    ))
    (assertContains "claude-sidecar-instructions-use-plain-text-reply" "plain text" (
      instructionsFor claudeSidecarEvaluated
    ))
    (assertion "service-lifetime-sidecar-lifetime" "service"
      claudeSidecarServiceLifetimeProcess.lifetime
    )
    (assertContains "service-lifetime-sidecar-carries-rotation-flag" "--daily-session-rotation"
      claudeSidecarServiceLifetimeProcess.command
    )
    (assertLacks "agent-lifetime-sidecar-omits-rotation-flag" "--daily-session-rotation"
      claudeSidecarProcess.command
    )
    (assertion "codex-auto-sidecar-enabled" "true" (stringify codexSidecarProcess.enabled))
    (assertion "codex-auto-sidecar-lifetime" "agent" codexSidecarProcess.lifetime)
    (assertLacks "codex-launch-command-drops-plugin-flags"
      "--channels plugin:discord@claude-plugins-official"
      codexLaunchCommand
    )
    (assertContains "embedded-agents-keep-marketplace-preactivation" "run" (
      claudeAutoEvaluated.config.clawde.channelAdapters.discord.preActivation or ""
    ))
    (assertion "sidecar-agents-skip-marketplace-preactivation" "null" (
      stringify (claudeSidecarEvaluated.config.clawde.channelAdapters.discord.preActivation or null)
    ))
    (assertion "all-sidecar-fleet-skips-marketplace-preactivation" "null" (
      stringify (codexSidecarEvaluated.config.clawde.channelAdapters.discord.preActivation or null)
    ))
  ];
}
