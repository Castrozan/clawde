# clawde performance: analysis and fix — live tracker

Branch: `perf/analysis-and-fix` (worktree `~/repo/clawde-perf`). Single source of live state; updated as last step of every increment.

## Goal
Profile the clawde agent loop, rank bottlenecks with evidence, implement and measure the highest-impact fixes. The 1M-context bump and outer-compaction are already done; do not redo.

## Loop map (verified by reading source)
- Supervisor `clawde-service.py`: reconciles every 10s. Per cycle per session: `pgrep -f wrapper` + `ps -ww -p PID` per matched pid + JSON config read per pid + `tmux list-panes` + `tmux rename-window` per mismatch. Runs unconditionally even when nothing changed.
- Heartbeat `driver.py`: wakes every minute boundary; on cron-matched minute runs `pane_is_idle` (1 tmux capture) + gate (`bash -c gate_command`). Steward gate = change-gate → `steward-heartbeat-probe` → `steward-status` (git fetch origin + `gh` CI API). Steward cron `*/15`.
- Wrapper `wrapper.py` + `session_watchdog.py`: restart loop; while agent runs, captures 80 pane lines every 30s.
- Discord Stop hook `enforce-discord-reply-stop-hook.py`: on EVERY turn-end, reads + `json.loads` the ENTIRE transcript jsonl.

## Live evidence (2026-06-27)
- Running: clawde-service (pid 17349), 4 wrappers, 1 heartbeat driver.
- Transcript sizes: 149 MB max; many 25-52 MB. Stop hook parses all of it per turn.

## Ranked bottlenecks (candidate, pre-verification)
1. **Discord Stop hook full-transcript parse per turn** — O(transcript) every turn-end; amplified by 1M bump (transcripts 25-50 MB). Fix: tail-scan only the bytes after the last user turn. HIGH.
2. **Supervisor full reconcile every 10s** — ~2+2N subprocesses/cycle (N agents) even when nothing changed; config file read per pid per cycle. Fix: skip expensive ps/config/rename when the pgrep pid-set is unchanged. MED-HIGH.
3. **steward-status git fetch + gh api on every call** — network-bound; runs in probe (15 min, gated) and on every agent steward-status. Fix: lower priority, cadence acceptable. LOW-MED.
4. **Duplicate pane/repl helpers + capture_pane_content** across modules — maintainability, minor. LOW.

## Adversarial analysis (35-agent workflow, ~1.04M tokens, all findings verified against source)
11 findings confirmed real + on hot path. Two are MED, rest LOW. Ranked:
1. MED discord stop hook full-transcript parse per turn — FIXED (I1). Live on the one discord-wired agent.
2. MED a2a observer forks 2 tmux subprocs/s/agent forever — DORMANT (a2a server not running for any live agent); deferred, fix sketch below.
3-7. LOW heartbeat git+gh+submodule+health storm every 15 min — gated background, verifiers rated the change-aware early-out UNSAFE (skipping gh/health/submodule when the cheap repo signals look clean can miss a same-head CI pending→failing transition). Deferred by design.
8-10. LOW supervisor: N×ps (FIXED I2), config-read-per-pid (verifier: caching unsafe), global pgrep O(S²N) (safe, marginal at S=2; deferred follow-up).
11. LOW a2a unbounded task output_text — dormant; deferred.

## Increments (done-per-increment = tests green + before/after measured + committed)
- [x] I0: baseline regression net — pytest 229 passed green on branch baseline.
- [x] I1 (91d1e97): discord stop hook tail-scan. Benchmark 47MB/8000-entry transcript, best of 5:
      common case 217.8ms→0.8ms (272x); 50-deep 217.2ms→36.0ms (6x). 10 hook tests green (5 new). Semantics identical.
- [x] I2 (b92e5da): supervisor single `ps -axww` scan vs pgrep+N×ps. Discovery forks 1+N→1 per session call
      (live 10→2 per cycle, ~48k fewer forks/day). 18 supervisor tests green (2 new). Matching identical to old pgrep -f.

## Deferred (real but not fixed, with reason)
- a2a observer idle-gating: a2a server is not running live; the safe fix is non-trivial (observe() does double duty — output-diff baseline + target-death watchdog — so a naive idle-skip corrupts output attribution and breaks the death watchdog). Safe sketch: liveness-only cheap poll when no active non-terminal task + reset diff baseline at task submit; the redundant second `list-windows` fork can also be derived from capture-pane success. Not worth the risk on a dormant path.
- heartbeat storm early-out: verifiers rated unsafe (correctness risk on same-head CI/submodule/health transitions). Submodule fetches could be parallelized (safe) but it is a 15-min gated background task, not on the agent's blocking path.
- supervisor one-scan-per-cycle (O(S²N)→O(SN)): safe but marginal at S=2; needs a call-chain refactor through ensure_all_agent_windows. Recommended follow-up.

## Assumptions
- assumed measurement via synthetic benchmarks (constructed large transcript, subprocess counters) is acceptable proof since live wrapper changes only apply on respawn; all edits are reversible and behavior-preserving.
- assumed I1's live target is the single discord-wired agent (hook wired per-discord-agent in workspace-files.nix); its transcript is daily-rotated so the per-turn parse cost grows through each day toward the benchmarked figures.
