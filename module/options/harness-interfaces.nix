{ lib, ... }:
let
  prePromptModalType = lib.types.submodule {
    options = {
      indicators = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        description = "Substrings that must ALL be present in a pane capture for this modal to be considered on screen.";
      };
      dismissKey = lib.mkOption {
        type = lib.types.str;
        default = "Enter";
        description = "Single key name sent to the pane to dismiss the modal, in the multiplexer's send-keys vocabulary.";
      };
    };
  };

  sessionIdentityType = lib.types.submodule {
    options = {
      generatesIdentifier = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Whether clawde mints the session identifier itself and hands it to the harness. False means the harness owns session identity and clawde reattaches positionally instead (codex 'resume --last', scoped by the agent's own harness home and workspace).";
      };
      freshArgvTemplate = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "Argv fragment placed right after the harness binary when starting a brand-new session. '{session_identifier}' is substituted when generatesIdentifier is true. Empty means a bare launch starts a fresh session.";
      };
      resumeArgvTemplate = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "Argv fragment placed right after the harness binary when continuing the previous session across a warm redeploy. May be a subcommand rather than a flag.";
      };
    };
  };

  sessionTranscriptStoreType = lib.types.submodule {
    options = {
      directoryTemplate = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "Path template of the directory holding one agent's session transcripts, with '{workspace_slug}' standing for the workspace path with every non-alphanumeric character dashed. Empty means the harness keeps its sessions somewhere clawde cannot probe, so a recorded session is trusted to still be resumable.";
      };
      fileNameTemplate = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = "File name template of a single session transcript inside directoryTemplate, with '{session_identifier}' substituted. Empty alongside directoryTemplate disables the probe.";
      };
    };
  };

  runtimeProfileType = lib.types.submodule {
    options = {
      liveProcessNameFragment = lib.mkOption {
        type = lib.types.str;
        description = "Substring identifying a live harness REPL among the agent wrapper's child processes. Used to tell a running agent from a dormant one before injecting a resume nudge.";
      };
      idlePromptLinePatterns = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        description = "Python regexes matched against each pane line. A pane whose capture has any matching line is considered parked at an idle prompt and safe to type into.";
      };
      onboardingIndicators = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = "Substrings whose presence means the harness is stuck at a login or first-run screen rather than at its prompt. Any match suppresses the idle verdict.";
      };
      usageLimitIndicators = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = "Substrings whose presence means the harness is parked on a quota-exhausted modal. Treated as stuck evidence so the watchdog restarts the session instead of waiting forever.";
      };
      missingResumeSessionIndicators = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = "Substrings the harness prints when it is asked to resume a session it can no longer find. Seeing one retires just that session identifier so the next launch falls back to remembered history instead of losing it.";
      };
      prePromptModals = lib.mkOption {
        type = lib.types.listOf prePromptModalType;
        default = [ ];
        description = "Modals the harness can raise before reaching its prompt that clawde is allowed to dismiss unattended.";
      };
      sessionIdentity = lib.mkOption {
        type = sessionIdentityType;
        default = { };
        description = "How this harness names sessions and how clawde reattaches to one across a warm redeploy.";
      };
      sessionTranscriptStore = lib.mkOption {
        type = sessionTranscriptStoreType;
        default = { };
        description = "Where this harness persists a session transcript, so clawde can tell a still-resumable session from one the harness has dropped.";
      };
    };
  };
in
{
  options.clawde.harnesses = lib.mkOption {
    type = lib.types.attrsOf (
      lib.types.submodule (
        { name, config, ... }:
        {
          options = {
            package = lib.mkOption {
              type = lib.types.nullOr lib.types.package;
              default = null;
              description = "The agent CLI package this harness launches. Injected by the consuming configuration; clawde pins no harness itself. Null means the harness is registered but unusable, and declaring an agent on it fails a build-time assertion.";
            };
            binaryName = lib.mkOption {
              type = lib.types.str;
              default = name;
              description = "Executable name resolved from the agent's runtime PATH rather than a store path, so a harness upgrade does not rewrite every agent launch command and force a cold respawn.";
            };
            binaryInvocation = lib.mkOption {
              type = lib.types.str;
              readOnly = true;
              default = "command ${config.binaryName}";
              description = "How a launch command must name the harness binary. Every builder below starts its command with this rather than with binaryName, because the command runs through a shell that expands aliases and shell functions before it ever consults PATH, so a user who aliases the harness name to a wrapper of their own silently replaces the flags clawde built with the wrapper's, and the harness dies at argument parsing. The command builtin resolves the name the way PATH says and leaves an alias no chance to rewrite it.";
            };
            defaultModel = lib.mkOption {
              type = lib.types.str;
              description = "Model identifier used by agents on this harness that set no model of their own and inherit none from their agent type.";
            };
            buildLaunchCommandFor = lib.mkOption {
              type = lib.types.functionTo lib.types.str;
              description = "Function: { name, agent, workspaceDirectory, instructionsFile, sessionArgvShellExpansion, channelLaunchFlags } -> the shell command that starts one agent REPL. Runs with the workspace already the working directory and the channel adapter's environment already exported.";
            };
            buildRunOnceCommandFor = lib.mkOption {
              type = lib.types.functionTo lib.types.str;
              description = "Function: { name, agent, workspaceDirectory, instructionsFile } -> the shell command that runs the agent's heartbeat prompt to completion and exits, for a launchOnTrigger agent that holds no warm session between firings.";
            };
            buildOneShotTurnCommandFor = lib.mkOption {
              type = lib.types.nullOr (lib.types.functionTo lib.types.str);
              default = null;
              description = "Function: { name, agent, workspaceDirectory, instructionsFile } -> the shell command that runs one turn of a conversation and exits, taking its prompt from $CLAWDE_CHANNEL_PROMPT, continuing the previous turn when $CLAWDE_CHANNEL_SESSION_CONTINUATION is non-empty, and leaving the assistant's reply and nothing else in the file named by $CLAWDE_CHANNEL_REPLY_FILE. Null means the harness has no headless mode, so channel adapters that drive it from a sidecar process cannot carry it.";
            };
            runtimeProfile = lib.mkOption {
              type = runtimeProfileType;
              description = "Everything the python runtime needs to read and drive this harness's pane. Serialized into each agent's launch config so the supervisor, watchdog, heartbeat driver and resume nudge stay data-driven instead of branching on the harness name.";
            };
            meaningfulOutputLinePattern = lib.mkOption {
              type = lib.types.str;
              description = "Regex matching the only pane lines that count as meaningful new agent output. Filters status-line and spinner redraws so the a2a peer adapter's idle auto-complete fires.";
            };
            workspaceFilesFor = lib.mkOption {
              type = lib.types.functionTo (lib.types.attrsOf lib.types.anything);
              default = _: { };
              description = "Function: { name, agent, workspaceDirectory, workspaceRelativeToHome } -> home.file entries materializing this harness's per-agent configuration, keyed relative to the home directory.";
            };
            agentActivationScriptFor = lib.mkOption {
              type = lib.types.functionTo lib.types.str;
              default = _: "";
              description = "Function: { name, agent, workspaceDirectory, harnessBinary } -> shell snippet appended to home.activation for harness-specific workspace seeding.";
            };
            preActivation = lib.mkOption {
              type = lib.types.nullOr lib.types.str;
              default = null;
              description = "Optional activation snippet run once when at least one agent uses this harness.";
            };
            unenforceableDenyToolPatternsFor = lib.mkOption {
              type = lib.types.functionTo (lib.types.listOf lib.types.str);
              default = { denyToolPatterns, ... }: denyToolPatterns;
              description = "Function: { name, agent, denyToolPatterns } -> the subset of the agent's deny patterns this harness can neither refuse at call time nor make unreachable by construction, which fails a build-time assertion so moving an agent between harnesses never silently drops a guardrail. A harness with a call-time denylist returns nothing. An inclusion-based harness, which grants capability by wiring rather than by refusal, returns only the patterns naming something it wires in anyway. The default calls every pattern unenforceable, the safe answer for a harness that has declared nothing.";
            };
            supportedChannelTypes = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ "none" ];
              description = "channel.type values this harness can actually serve. An agent pairing a channel this harness cannot transport fails a build-time assertion rather than launching into a session that can never receive a message.";
            };
            embeddedChannelTypes = lib.mkOption {
              type = lib.types.listOf lib.types.str;
              default = [ "none" ];
              description = "channel.type values this harness serves in-process (plugin, native channel support) with no sidecar bridge. The total supportedChannelTypes is the union of what embeds and what a one-shot turn command can bridge; channel adapters pick embedded transport when this list carries the channel and fall back to the sidecar bridge otherwise.";
            };
            packages = lib.mkOption {
              type = lib.types.listOf lib.types.package;
              default = [ ];
              description = "Packages added to home.packages only when at least one agent on this harness is declared on the host.";
            };
          };
        }
      )
    );
    default = { };
    description = "Harness implementations. Each module that wants to provide a new agent.harness registers itself here.";
  };
}
