{
  description = "clawde - declarative persistent Claude Code agents as a home-manager module";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";

  outputs =
    { self, nixpkgs }:
    let
      inherit (nixpkgs) lib;
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

      checks = import ./checks {
        inherit
          self
          nixpkgs
          lib
          forAllSystems
          ;
      };

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
