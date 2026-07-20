# clawde

Declarative, persistent Claude Code agents as a home-manager module.

clawde supervises long-lived Claude Code sessions as tmux windows, each driven by an
optional cron heartbeat, exposed over channel adapters (Discord) and peer adapters (A2A),
with per-agent personality, model, permission mode, skill directories, and agent-type
defaults. A single service reconciles every declared agent on the host.

## Usage

Add the flake as an input and import its home-manager module:

```nix
{
  inputs.clawde.url = "github:castrozan/clawde";
  inputs.clawde.inputs.nixpkgs.follows = "nixpkgs";
}
```

```nix
{ inputs, ... }:
{
  imports = [ inputs.clawde.homeManagerModules.default ];

  clawde.claudePackage = pkgs.claude-code;

  clawde.agents.my-agent = {
    type = "generic";
    personality = "You are my-agent.";
  };
}
```

Keep `inputs.clawde.inputs.nixpkgs.follows = "nixpkgs"` set: clawde's input set is
deliberately nixpkgs-only, so following your nixpkgs keeps the downstream lock free of
clawde-specific entries.

The consuming configuration injects the host-specific wiring the module does not own:

- `clawde.claudePackage` - the claude-code package agents launch.
- `clawde.machinesRegistry` - fleet topology keyed by host alias (platform and, for the
  steward, tailscaleIp/username), used to build `fleet.json` and `host-identity.json`.
- `clawde.dotfilesRepoPath` - the checkout this fleet member tracks (defaults to ~/.dotfiles).
- `clawde.stewardLiveCheckoutPayloadPath` - optional live editable steward payload path; null
  symlinks the immutable in-store payload.
- `healthCheckLib` (module arg) - optional; when present, clawde contributes health probes.

### On-demand agents

An agent declared with `onDemand = true` is never brought up by the supervisor on its
own. It holds no process and no multiplexer window until an operator starts it:

```nix
clawde.agents.my-agent = {
  type = "project-manager";
  onDemand = true;
  idleTimeoutMinutes = 30;
};
```

```
clawde start my-agent
clawde stop my-agent
clawde list
```

The module installs a bash completion under `share/bash-completion/completions/clawde`,
so the subcommands complete, `start`/`stop` offer only the agents declared `onDemand`,
and `active` offers only the agents that actually have an active-hours gate.

`clawde start` writes a lease under `~/clawde/on-demand/<agent>.json` and the supervisor
brings the agent up on its next poll. The lease survives until the agent's session
transcript has been silent for `idleTimeoutMinutes`, at which point the supervisor tears
the agent down through the same path it uses for an agent outside its active hours. The
idle clock is floored at the moment the lease was granted, so starting an agent whose
last conversation was days ago does not stop it immediately.

The agent's session record outlives the teardown, so the next `clawde start` resumes the
same conversation rather than making the operator find it. Set `dailySessionRotation`
if a fresh session per day is wanted instead. `activeHoursStart`/`activeHoursEnd` still
apply on top: an on-demand agent outside its active hours stays stopped despite a lease.

## Outputs

- `homeManagerModules.default` / `homeManagerModules.clawde` - the module.
- `stewardPayloadPath` - path to the steward agent-type payload, for steward declarations.
- `injectAgentIdentity` - helper that interpolates fleet identity into an agent personality.
- `checks.<system>.unit-tests` - the agent-wrapper, heartbeat, service, steward, and a2a-server
  python unit suites.

## Repo layout

```
flake.nix              plain flake: inputs.nixpkgs only; exports the module, helpers, and checks
flake.lock
README.md
.gitignore
module/
  default.nix          imports every options/, config/, and adapter module
  options/             module interface: option declarations and type contracts
    interfaces.nix
    agent-type-interfaces.nix
    host-wiring-interfaces.nix
    options.nix
  lib/                 pure nix helpers (no config): identity injection, window specs, paths
    inject-agent-identity.nix
    agent-window-spec.nix
    runtime-locations.nix
    runtime-paths.nix
    lib.nix
  config/              the config side of the module: what the options resolve into
    activations.nix
    agent-assertions.nix
    fleet.nix
    health.nix
    host-identity.nix
    instruction-files.nix
    launch-config-files.nix
    service.nix
    workspace-files.nix
  agent-types/         per-type defaults (generic, project-manager, steward + its payload)
  channel-adapters/    user-facing channels (discord)
  peer-adapters/       agent-to-agent transport (a2a server)
  instructions/        runtime instruction markdown injected into agents
  scripts/             python/bash runtime: agent-wrapper, heartbeat, clawde-service
    tests/             pytest suites mirroring the runtime scripts
  snippets/            reusable instruction fragments
```

The `options/` -> `lib/` -> `config/` split is the spine: `options/` declares the interface,
`lib/` holds pure helpers with no config dependency, and `config/` is the only side that reads
options and produces home-manager config, files, and the reconcile service.

## Development

The flake provides a dev shell with every toolchain the repo uses (python312 + pytest, nix
formatting and linting, shfmt, shellcheck):

```sh
nix develop
```

Format the whole tree (nix via nixfmt, python via ruff, shell via shfmt):

```sh
nix fmt
```

Run the full gate - evaluates the flake and runs the unit suites on the current system:

```sh
nix flake check
```

Run pytest directly while iterating (faster than a full `nix flake check`; needs `tmux` on
PATH and a writable `HOME`, both provided by `nix develop`):

```sh
python -m pytest -q \
  module/scripts/tests/unit \
  module/agent-types/steward/payload/tests/unit \
  module/peer-adapters/a2a/a2a_server/tests
```

Narrow to one suite or one file the same way, for example:

```sh
python -m pytest -q module/scripts/tests/unit/test_wrapper.py
```

### Conventions

These are enforced by review, not just tooling:

- Zero comments in any language - no inline comments, docstrings, banners, or TODO notes.
  Names carry the meaning: long, descriptive, unabbreviated identifiers. A `shellcheck`
  directive is a functional pragma, not a comment, and is allowed.
- Python 3.12 is the default for scripts. Bash is only for thin glue over shell-native tools.
- Single responsibility per function and per file.
- Test-first when fixing a bug: write the failing test, then fix.
- Never present code that has not been built and tested. For nix, a successful eval/build is
  the verification.
- Nix is formatted with nixfmt and linted with statix + deadnix; python is formatted and
  linted with ruff; bash is formatted with shfmt and linted with shellcheck.

See `AGENTS.md` for the full machine-readable form of these rules.

## Testing

The `checks.<system>.unit-tests` derivation is a `runCommand` that runs pytest over a copy of
the source with `tmux` on PATH and `HOME` / `TMUX_TMPDIR` pointed at fresh temp dirs. It
covers three suites totalling 181 tests:

- `module/scripts/tests/unit` - the agent runtime. The agent-wrapper (launch, stuck-indicator
  detection, pane responsiveness, session watchdog, restart scheduling, redeploy signals,
  resume nudge), the heartbeat (cron scheduling, tmux driver, change-gate edge triggering),
  the clawde-service reconcile (window-name and agent-identity reconciliation), clawde-redeploy,
  and the Discord reply stop hook.
- `module/agent-types/steward/payload/tests/unit` - the steward agent payload. Repository,
  submodule, and CI status probes, health summary, the heartbeat probe, and the
  activate/status/msg entry points.
- `module/peer-adapters/a2a/a2a_server/tests` - the A2A peer server. Agent card, task store,
  active-task coordinator watchdog, and the tmux backend (observe, send-input, meaningful-line
  extraction), plus the server and subprocess-backend integration tests.

Tests mock subprocess interactions; the ones that exercise tmux need a real `tmux` binary and a
writable `HOME`, which `nix develop` and the check derivation both supply.

The suites run across all supported systems via `forAllSystems`:
`x86_64-linux`, `aarch64-linux`, `x86_64-darwin`, `aarch64-darwin`.

## CI

CI runs the same gate a developer runs locally, so a green local `nix flake check` predicts a
green pipeline:

- `nix flake check` - evaluates the flake and runs `checks.<system>.unit-tests` (the 181-test
  suite) on the CI runner's system.
- `nix fmt -- --check` (or the equivalent per-tool checks) - fails the build on any file that
  is not formatted by nixfmt / ruff / shfmt.
- statix + deadnix over the nix tree, ruff over python, shellcheck over bash - lint gates that
  match the conventions above.

CI is the only authority on green; the repo is kept synced and pushed only after the gate
passes.
