# Claude Code Configuration

This is the clawde home-manager module - a Nix flake exporting persistent Claude Code agent definitions.

## Authoritative Reference

See **AGENTS.md** for:
- Repository structure (module/, scripts/, agent-types/, channel-adapters/, peer-adapters/).
- Build, test, and lint commands (`nix flake check`, `ruff`, `shfmt`/`shellcheck`).
- Hard conventions: zero comments, long descriptive names, Python 3.12 default, bash for thin shell glue, single responsibility, test-first bug fixes, never present unbuilt/untested code.

## Quick Start

```bash
nix flake check              # Run all tests and linting
nix develop                  # Enter dev shell with Nix, Python 3.12, pytest, ruff, nixfmt, shfmt, shellcheck, tmux
```

## Claude Code Specifics

When editing agent configuration, instructions, or scripts in this repo:

1. Follow AGENTS.md conventions exactly: no comments, descriptive names, single responsibility.
2. Build/test locally: `nix flake check` is your verification gate.
3. For Python scripts, run `ruff format && ruff check` before committing.
4. For bash, run `shfmt -w && shellcheck` before committing.
5. For .nix files, run `nixfmt` and verify `nix flake check` passes.
6. Commit frequently; the steward loop reconciles against origin/main, so manual push/rebase is unnecessary.

## Inputs

Consumers should lock clawde's nixpkgs input:

```nix
inputs.clawde.inputs.nixpkgs.follows = "nixpkgs";
```

This keeps lock files minimal and avoids input-set bloat.

## Testing

All 181 unit tests pass via `nix flake check`:
- `module/scripts/tests/unit/` - Shared utility tests.
- `module/agent-types/steward/payload/tests/unit/` - Steward agent tests.
- `module/peer-adapters/a2a/a2a_server/tests/` - Agent-to-agent coordination tests.

Tests mock subprocess, set HOME and TMUX_TMPDIR, and verify agent lifecycle, credential injection, and channel/peer adapter behavior.

## Useful Paths

- `module/lib/inject-agent-identity.nix` - Agent identity injection logic (re-exported as injectAgentIdentity).
- `module/agent-types/steward/payload/` - Steward agent payload (re-exported as stewardPayloadPath).
- `module/instructions/` - Agent instruction templates.
- `module/config/` - Core module configuration logic.
