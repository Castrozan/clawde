{
  pkgs,
  lib,
  module,
}:
let
  evaluation = import ../discord-transport/support/evaluation.nix { inherit pkgs lib module; };
  evaluated = evaluation.evaluatedFor (
    evaluation.discordAgentConfig {
      harness = "claude";
      transport = "sidecar";
      lifetime = "agent";
    }
  );
  launchConfig = pkgs.writeText "channel-launch-config.json" (
    evaluated.config.home.file."clawde/launch-config/fixture-agent.json".text
  );
  fakeHarnesses =
    map
      (
        name:
        pkgs.writeShellScriptBin name ''
          exec ${pkgs.python312}/bin/python3 ${./harness_fixture.py} ${name} "$@"
        ''
      )
      [
        "claude"
        "codex"
        "opencode"
      ];
in
pkgs.runCommand "clawde-channel-turn-execution" { nativeBuildInputs = fakeHarnesses; } ''
  export PYTHONPATH=${../../channel-adapters/discord/scripts}
  ${pkgs.python312}/bin/python3 ${./verify_turns.py} ${launchConfig}
  touch "$out"
''
