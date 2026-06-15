{ ... }:
{
  imports = [
    ./options/interfaces.nix
    ./options/agent-type-interfaces.nix
    ./options/host-wiring-interfaces.nix
    ./options/options.nix
    ./config/agent-assertions.nix
    ./agent-types
    ./config/host-identity.nix
    ./config/fleet.nix
    ./config/workspace-files.nix
    ./config/instruction-files.nix
    ./config/launch-config-files.nix
    ./config/activations.nix
    ./config/service.nix
    ./channel-adapters/discord
    ./peer-adapters/a2a
    ./config/health.nix
  ];
}
