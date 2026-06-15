# clawde Agent Instructions

Home-manager module exporting persistent Claude Code agents via Nix configuration.

## Purpose

clawde is a private Nix flake that provides a home-manager module for declaratively configuring Claude Code agents. It handles agent lifecycle, MCP integration, credential management via agenix, channel adapters (Discord, HTTP), and peer-to-peer agent coordination.

## Repository Structure

- `flake.nix` - Nix flake entry point; outputs homeManagerModules.clawde, homeManagerModules.default, stewardPayloadPath, injectAgentIdentity, checks.
- `flake.lock` - Locked nixpkgs input (nixos-25.11); consumable projects should follow this via inputs.clawde.inputs.nixpkgs.follows = "nixpkgs".
- `README.md` - User-facing module documentation.
- `.gitignore` - Standard ignore patterns.
- `module/` - Core module.
  - `default.nix` - Module entry point.
  - `options/` - Home-manager option definitions.
  - `lib/` - Shared library functions, including inject-agent-identity.nix for agent config injection.
  - `config/` - Module implementation.
  - `scripts/` - Shared utility scripts (Python 3.12, bash thin-glue only).
  - `scripts/tests/unit/` - Unit tests (pytest 3.12) with subprocess mocking; some require writable HOME + tmux.
  - `agent-types/` - Agent-type implementations (generic, project-manager, steward).
  - `agent-types/steward/payload/` - Steward agent payload; stewardPayloadPath export points here.
  - `agent-types/steward/payload/tests/unit/` - Steward unit tests.
  - `channel-adapters/` - Channel-specific adapters (Discord bot, HTTP gateway).
  - `peer-adapters/a2a/` - Agent-to-agent coordination adapter.
  - `peer-adapters/a2a/a2a_server/tests/` - A2A server unit tests.
  - `instructions/` - Agent instruction templates and system prompts.
  - `snippets/` - Code/config snippets for reference and reuse.

## Build, Test, and Lint

### Nix

```bash
nix flake check              # Run all checks (unit tests + lint)
nix fmt                      # Format .nix files (nixfmt)
statix .                     # Lint .nix files
deadnix .                    # Detect dead code in .nix
nix develop                  # Enter dev shell with tools
```

### Python

```bash
pytest module/scripts/tests/unit module/agent-types/steward/payload/tests/unit module/peer-adapters/a2a/a2a_server/tests
ruff format module/          # Format Python 3.12 code
ruff check module/           # Lint Python 3.12 code
```

### Bash

```bash
shfmt -w module/            # Format bash scripts
shellcheck module/**/*.sh    # Lint bash scripts (shellcheck directives allowed as pragmas)
```

### Integration

```bash
nix flake check              # Primary verification: runs pytest via pkgs.runCommand across all test dirs
```

The check output includes 181 passing unit tests across scripts/, agent-types/steward/payload/, and peer-adapters/a2a/. Tests mock subprocess; tmux and HOME environment are available.

## Hard Conventions

### Code Style

- **Zero comments**: No inline comments, docstrings, TODO notes, or commented-out code in any language. Names carry all meaning; use long, descriptive function, variable, file, and directory names.
- **Single Responsibility**: Each function does one thing; each script has one purpose. Split oversized functions.
- **Language Defaults**:
  - Python 3.12 for all non-trivial scripts.
  - Bash only for thin wrappers around shell-native tools (tmux send-keys, fzf, sysctl pipelines); avoid bash where Python subprocess.run is clearer.
  - Nix for module logic and configuration.

### Testing

- **Test-First for Bugs**: When a bug is reported, write a failing test first. The test passing is proof the bug is fixed.
- **No Unbuilt Code**: Never present code that has not been rebuilt and tested. For .nix files, a successful `nix flake check` or `nix build` IS the primary verification. For Python, all pytest must pass.
- **Pragmatic Mocking**: Tests mock subprocess calls; some require writable HOME and tmux for integration.

### Nix-Specific

- Long inline scripts (>10 lines of logic) must live in dedicated files under `scripts/` or `agent-types/*/scripts/`, not inline in `.nix` files via `pkgs.writeShellScript`.
- Format with `nixfmt`; lint with `statix` and `deadnix`.
- Avoid adding inputs beyond nixpkgs; prefer nixpkgs-scoped tooling (e.g., treefmt-nix is not necessary; use raw nixfmt/statix/deadnix).

### Python-Specific

- Python 3.12; no uv, venv, or pip. Scripts run via Nix.
- Format and lint with `ruff format` and `ruff check`.
- Unit tests use pytest with subprocess mocking.

### Bash-Specific

- Format with `shfmt -w`; lint with `shellcheck`.
- Shellcheck directives (e.g., `# shellcheck disable=SC1234`) are allowed as functional pragmas, not workarounds for bad code.
- Bash scripts must be thin wrappers; complex logic goes to Python.

## Flake Outputs

```nix
outputs = forAllSystems [ x86_64-linux aarch64-linux x86_64-darwin aarch64-darwin ]:
  {
    homeManagerModules.clawde = import ./module;
    homeManagerModules.default = import ./module;
    stewardPayloadPath = ./module/agent-types/steward/payload;
    injectAgentIdentity = import ./module/lib/inject-agent-identity.nix;
    checks.<system>.unit-tests = pkgs.runCommand "clawde-unit-tests" { ... } ''pytest ...'';  # 181 tests
  }
```

### Consumers

Set `inputs.clawde.inputs.nixpkgs.follows = "nixpkgs"` to keep lock files clean and avoid input bloat.

## Agent Types

- **generic**: Base agent type; all agents inherit from this.
- **project-manager**: Project-scoped agents with elevated context and tool access.
- **steward**: Autonomous repository steward; reconciles git state, validates builds, pushes changes.

Type defaults are resolved at consumption sites, never in submodule config, to avoid infinite recursion.

## Channel Adapters

- **Discord**: Bot token via agenix; routes incoming Discord messages to agent queues.
- **HTTP**: RESTful agent invocation gateway.

Both are declaratively configured; credentials are encrypted at rest.

## Peer-to-Peer Coordination

The a2a (agent-to-agent) adapter enables Claude Code agents running on different machines to coordinate work, share state, and delegate subtasks. MCP-integrated for transparent message passing.
