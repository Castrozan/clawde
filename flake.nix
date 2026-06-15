{
  description = "clawde - declarative persistent Claude Code agents as a home-manager module";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

  outputs =
    { self, nixpkgs }:
    let
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      homeManagerModules.clawde = import ./module;
      homeManagerModules.default = self.homeManagerModules.clawde;

      stewardPayloadPath = ./module/agent-types/steward/payload;
      injectAgentIdentity = import ./module/lib/inject-agent-identity.nix;

      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonForUnitTests = pkgs.python312.withPackages (pythonPackages: [ pythonPackages.pytest ]);
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
        }
      );

      formatter = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        pkgs.writeShellApplication {
          name = "clawde-fmt";
          runtimeInputs = [
            pkgs.nixfmt-rfc-style
            pkgs.ruff
            pkgs.shfmt
            pkgs.findutils
          ];
          text = ''
            find . -name '*.nix' -print0 | xargs -0 --no-run-if-empty nixfmt

            ruff format .

            find . -name '*.sh' -print0 | xargs -0 --no-run-if-empty shfmt -w
          '';
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonForDevShell = pkgs.python312.withPackages (pythonPackages: [ pythonPackages.pytest ]);
        in
        {
          default = pkgs.mkShell {
            packages = [
              pythonForDevShell
              pkgs.jq
              pkgs.tmux
              pkgs.nixfmt-rfc-style
              pkgs.statix
              pkgs.deadnix
              pkgs.ruff
              pkgs.shfmt
              pkgs.shellcheck
            ];
          };
        }
      );
    };
}
