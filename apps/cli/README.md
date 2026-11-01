# gilberto CLI

Workspace for the `gilberto` binary. `pnpm --filter gilberto build` emits `dist/cli.js` (executable).

## Install (alpha)

```bash
npx gilberto@next --version
```

Requires Node ≥ 22.12. Published on npm tag `next`.

## Layout

- `src/cli.ts` — Commander entry point (placeholder until #37)
- `src/index.ts` — library entry
- `src/{config,registry,commands,ui,test-utils}/`, `src/diagnostics.ts` — aliased via `#config`, `#registry`, `#commands`, `#ui`, `#test-utils`, `#diagnostics` (`tsconfig.json > paths`)

## `gilberto install [target]`

Wizard steps 1-8 (steps 1-3 never write; steps 4-6 write only inside a temp dir, then moves it atomically; steps 7-8 run on the written vault):

1. target path — positional arg or prompt (default `~/Dropbox/Gilberto/`); `~`/`$HOME` expanded
2. overwrite check — vault marker (`anatomy/anatomy.md` or `.claude/skills/gilberto-*`) aborts; other existing path asks `Target path exists. Continue?` (default No)
3. topic seeds — one multi-select per `pulse`, `intelligence`, `projects`
4. skeleton — builds `$TMPDIR/gilberto-install-<pid>/`, then a single rename puts it at the target (cross-device: copy to a sibling staging dir, then rename). Any failure or Ctrl+C removes the temp dir and leaves the target untouched. Materialized layout:

```text
me/me.md  journey/journey.md  network/network.md  network/{people,companies}/
pulse/pulse.md  pulse/<topic>/<topic>.md  pulse/<topic>/history/
intelligence/intelligence.md  intelligence/<topic>/<topic>.md
projects/projects.md  projects/<topic>/<topic>.md
_ingest/.gitkeep  anatomy/  .claude/skills/  CLAUDE.md
```

Folder-notes come from `@foomakers/gilberto-vault-bootstrap` templates; topics from step 3.

5. plugins — prints the bundled first-party plugins, one line each (info only: no prompt, no install)
6. anatomy — copies `seed/anatomy/` from `@foomakers/gilberto-vault-bootstrap` into `<tmp>/anatomy/` before the commit (`.md`: `{{DATE}}` → install date; other files byte-copied; one `| <topic> | |` row per seeded topic appended to `topics.md`). Missing package/seed → `vault-bootstrap content package not found; reinstall gilberto`, unreadable seed file → `failed to seed anatomy: <path>`; both exit 70, temp removed, target untouched. Ctrl+C → exit 130 as step 4
7. hooks — JSON-merges three Claude Code hooks into `<vault>/.claude/settings.json` (atomic tmp + rename), dispatchers in `<vault>/.claude/hooks/`. User keys/hooks are preserved; a gilberto hook already pointing elsewhere triggers `settings.json.bak-<ISO8601>` then overwrite. Invalid JSON → exit 65, file untouched.
8. launchd — macOS: writes 3 plists to `~/Library/LaunchAgents/`, `plutil -lint` each, never `launchctl` (written, not loaded; each process skill activates its job on install; `gilberto status` reports inactive jobs). Linux: prints `linux scheduling stub: cron/systemd timers land in Initiative #5`, writes nothing. `CI=true` skips unless `--launchd-in-ci`.

Hook ids (command basename `<id>.sh`): `gilberto.session-start` (`SessionStart` → `/gilberto-process-next`, off via `- session-start: off` in `anatomy/preferences.md`), `gilberto.pre-compact` (`PreCompact` → `/gilberto-process-capture`), `gilberto.session-end` (`SessionEnd` → `/gilberto-process-reflect day`, first end of the day). Dispatchers exit 0 and log `skill not installed: <skill>` when the skill is absent. Targets Claude Code hooks schema `{hooks: {Event: [{matcher, hooks: [{type: "command", command}]}]}}` (current at time of writing).

Plists (`RunAtLoad=false`): `com.foomakers.gilberto.morning-briefing` (07:00, `/gilberto-process-surface morning-briefing`), `com.foomakers.gilberto.reflect-day` (22:00, `/gilberto-process-reflect day`), `com.foomakers.gilberto.ingest` (`WatchPaths` `<vault>/_ingest/`, `/gilberto-process-ingest`). Jobs run `claude -p` (resolved from `PATH` at install, else `claude`), not the `gilberto` CLI. Re-run install after moving `claude`.

Flags:

- `--seed-topics <list>` — `pillar=a,b;pillar=c`; skips step 3 prompts, unnamed pillars keep defaults
- `--non-interactive` — never prompt; `target` required
- `--no-hooks` — skip step 7; `--no-launchd` — skip step 8; `--launchd-in-ci` — write plists even when `CI=true`
- `-v, --verbose` — one `key=value` line per decision, plus `wrote dir="<rel>"` / `wrote file="<rel>"` per item of steps 4, 7, 8, and `merged-keys=<list>` for step 7

Exit codes: `0` declined overwrite, `1` target is a file, `2` vault exists, `13` not writable, `28` disk full, `64` missing/invalid input, `65` invalid settings.json / plist validation / plutil missing, `70` vault-bootstrap package missing, `130` Ctrl+C.

## Smoke

CI workflow `.github/workflows/bootstrap-smoke.yml` runs `test/smoke/bootstrap.sh` on ubuntu/macOS × Node 22/24 against the packed CLI. Local re-run: `pnpm cli:smoke` (builds, packs, installs to a temp prefix; `pnpm cli:smoke launchd` on macOS for the plist branch, HOME redirected to a temp dir). Assertions: `test/smoke/assertions.sh`. Prints `metric: install_duration_seconds=<n>`; budget 180s (`SMOKE_BUDGET_SECONDS`). `SMOKE_STEPS_5_6=1` also asserts plugins/anatomy steps (owned by #58).
