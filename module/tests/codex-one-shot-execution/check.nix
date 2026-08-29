{
  pkgs,
  lib,
  module,
}:
let
  codexEvaluation = import ../discord-transport/support/evaluation.nix {
    inherit pkgs lib module;
  };
  evaluatedConfig = codexEvaluation.evaluatedFor (
    codexEvaluation.discordAgentConfig {
      harness = "codex";
      transport = "auto";
      lifetime = "agent";
    }
  );
  launchConfigText = evaluatedConfig.config.home.file."clawde/launch-config/fixture-agent.json".text;
  parsedLaunchConfig = builtins.fromJSON (builtins.unsafeDiscardStringContext launchConfigText);
  codexOneShotCommand = lib.addContextFrom launchConfigText parsedLaunchConfig.harness_one_shot_turn_commands.codex;
in
pkgs.runCommand "clawde-codex-one-shot-execution" { } ''
  set -euo pipefail

  fake_binary_directory=$(mktemp -d)
  cat > "$fake_binary_directory/codex" <<'FAKECODEX'
  #!${pkgs.bash}/bin/bash
  set -euo pipefail
  output_path=""
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "--output-last-message" ]; then
      output_path="$2"
      shift 2
    else
      shift
    fi
  done
  cp "$FAKECODEX_ENVELOPE_FILE" "$output_path"
  FAKECODEX
  chmod +x "$fake_binary_directory/codex"

  turn_directory=$(mktemp -d)
  envelope_path="$turn_directory/envelope.json"
  printf '%s' '{"action":"reply","text":"hello there"}' > "$envelope_path"
  export FAKECODEX_ENVELOPE_FILE="$envelope_path"
  export CLAWDE_CHANNEL_REPLY_FILE="$turn_directory/reply.txt"
  export CLAWDE_CHANNEL_PROMPT="ping"
  export PATH="$fake_binary_directory:$PATH"
  codex_one_shot_command=${lib.escapeShellArg codexOneShotCommand}
  bash -c "$codex_one_shot_command"

  if [ "$(cat "$CLAWDE_CHANNEL_REPLY_FILE")" != "hello there" ]; then
    echo "FAIL: reply file did not receive the model text" >&2
    exit 1
  fi
  if [ ! -f "$CLAWDE_CHANNEL_REPLY_FILE.codex-turns" ]; then
    echo "FAIL: structured sidecar output was not written" >&2
    exit 1
  fi

  silence_directory=$(mktemp -d)
  silence_envelope_path="$silence_directory/envelope.json"
  printf '%s' '{"action":"silence","text":""}' > "$silence_envelope_path"
  export FAKECODEX_ENVELOPE_FILE="$silence_envelope_path"
  export CLAWDE_CHANNEL_REPLY_FILE="$silence_directory/reply.txt"
  bash -c "$codex_one_shot_command"
  if [ -e "$CLAWDE_CHANNEL_REPLY_FILE" ]; then
    echo "FAIL: silence left a public reply file" >&2
    exit 1
  fi

  touch "$out"
''
