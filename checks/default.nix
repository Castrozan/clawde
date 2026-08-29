{
  self,
  nixpkgs,
  lib,
  forAllSystems,
}:
let
  globalRuntimeInstructions = import ../module/instructions/global-runtime.nix;
  normalizedGlobalRuntimeInstructions = lib.toLower globalRuntimeInstructions;
  globalRuntimeMaximumBytes = 5000;
  globalRuntimeForbiddenFragments = [
    ".dotfiles"
    "heartbeat.md"
    "home-manager"
    "nixos"
    "`nix"
    "obsidian"
    "second brain"
    "webfetch"
    "gh run"
    "git agent-session"
    "claude-gpt"
    "claude code"
    "clawde"
    "codex"
    "opencode"
    "herdr"
    "a2a"
    "discord"
    "project manager"
    "steward"
    "tmux"
    "systemd"
    "/compact"
    "--resume"
    "rebuild"
    "python 3.12"
  ];
  globalRuntimeContainsOnlyUniversalPolicy = builtins.all (
    fragment: !(lib.hasInfix fragment normalizedGlobalRuntimeInstructions)
  ) globalRuntimeForbiddenFragments;
  globalRuntimeStaysUniversal =
    builtins.stringLength globalRuntimeInstructions <= globalRuntimeMaximumBytes
    && globalRuntimeContainsOnlyUniversalPolicy;
in
forAllSystems (
  system:
  let
    pkgs = nixpkgs.legacyPackages.${system};
    pythonForUnitTests = pkgs.python312.withPackages (pythonPackages: [ pythonPackages.pytest ]);
    discordTransportFixture = import ../module/tests/discord-transport/fixture.nix {
      inherit pkgs lib;
      module = self.homeManagerModules.clawde;
    };
    checkAssertion =
      assertion:
      let
        actual = lib.escapeShellArg assertion.actual;
        expected = lib.escapeShellArg assertion.expected;
      in
      ''
        actual=${actual}
        expected=${expected}
        if [ "$actual" != "$expected" ]; then
          echo "FAIL ${assertion.name}"
          echo "  expected: $expected"
          echo "  actual:   $actual"
          exit 1
        fi
      '';
  in
  {
    unit-tests =
      pkgs.runCommand "clawde-unit-tests"
        {
          nativeBuildInputs = [
            pythonForUnitTests
            pkgs.tmux
          ];
        }
        ''
          cp -r ${self} source
          chmod -R u+w source
          cd source
          export HOME="$(mktemp -d)"
          export TMUX_TMPDIR="$(mktemp -d)"
          python -m pytest -p no:cacheprovider -q \
            module/scripts/tests/unit \
            module/agent-types/steward/payload/tests/unit \
            module/peer-adapters/a2a/a2a_server/tests
          touch "$out"
        '';

    discord-transport-eval = pkgs.runCommand "clawde-discord-transport-eval" { } (
      lib.concatStringsSep "\n" (map checkAssertion discordTransportFixture.assertions) + "\ntouch $out"
    );

    codex-one-shot-execution = import ../module/tests/codex-one-shot-execution/check.nix {
      inherit pkgs lib;
      module = self.homeManagerModules.clawde;
    };

    formatting =
      pkgs.runCommand "clawde-formatting"
        {
          nativeBuildInputs = [
            pkgs.nixfmt-rfc-style
            pkgs.ruff
            pkgs.shfmt
            pkgs.findutils
          ];
        }
        ''
          cp -r ${self} source
          chmod -R u+w source
          cd source

          find . -name '*.nix' -print0 | xargs -0 nixfmt --check

          ruff format --check .

          find . -name '*.sh' -print0 | xargs -0 shfmt -d

          touch "$out"
        '';

    lint =
      pkgs.runCommand "clawde-lint"
        {
          nativeBuildInputs = [
            pkgs.statix
            pkgs.deadnix
            pkgs.ruff
            pkgs.shellcheck
            pkgs.findutils
          ];
        }
        ''
          cp -r ${self} source
          chmod -R u+w source
          cd source

          statix check .

          deadnix --fail .

          ruff check .

          find . -name '*.sh' -print0 | xargs -0 shellcheck

          touch "$out"
        '';

    global-runtime-stays-universal =
      assert lib.assertMsg globalRuntimeStaysUniversal (
        "clawde-runtime.md must stay below the global context budget and contain only cross-harness, "
        + "cross-domain policy; move repository, harness, tool, and capability mechanics to their owning surfaces"
      );
      pkgs.runCommand "clawde-global-runtime-stays-universal" { } ''
        touch "$out"
      '';
  }
)
